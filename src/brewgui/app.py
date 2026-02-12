import tkinter as tk
from tkinter import ttk, messagebox
import subprocess
import threading
import random


# ==============================
# 单个安装任务
# ==============================
class InstallTask:
    def __init__(self, app, package, container):
        self.app = app
        self.package = package
        self.container = container
        self.process = None
        self.thread = None
        self.progress_value = 0
        self.output_lines = []
        self.max_log_lines = 200  # 只保留最后 200 行，防止卡顿
        self.create_ui()

    def create_ui(self):
        self.frame = tk.Frame(self.container, bd=1, relief="solid", padx=8, pady=6)
        self.frame.pack(fill="x", pady=4)

        top_row = tk.Frame(self.frame)
        top_row.pack(fill="x")

        self.title = tk.Label(top_row, text=self.package, font=("Arial", 11, "bold"))
        self.title.pack(side="left", anchor="w")

        self.status = tk.Label(top_row, text="安装中...", fg="gray")
        self.status.pack(side="right", anchor="e")

        self.progress = ttk.Progressbar(self.frame, maximum=100)
        self.progress.pack(fill="x", pady=(6, 4))

        # 进度条下方直接显示日志
        self.log_text = tk.Text(
            self.frame,
            height=6,
            wrap="word",
            font=("Menlo", 11),
            relief="flat",
            bg=self.frame.cget("bg"),
        )
        self.log_text.pack(fill="x", pady=(0, 2))
        self.log_text.config(state="disabled")

    def start(self):
        self.thread = threading.Thread(target=self.run, daemon=True)
        self.thread.start()

    def run(self):
        try:
            self.process = subprocess.Popen(
                f"brew install {self.package}",
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True
            )

            for line in self.process.stdout:
                line = line.rstrip("\n")
                self.output_lines.append(line)

                # 只保留最后 max_log_lines 行（避免 output_lines 无限增长）
                if len(self.output_lines) > self.max_log_lines:
                    self.output_lines = self.output_lines[-self.max_log_lines:]

                # 追加到界面日志
                self.append_log(line)

                self.simulate_progress(line)

            self.process.wait()

            if self.process.returncode == 0:
                self.update_status("完成", "green")
                self.update_progress(100)
            else:
                self.update_status("失败", "red")
                self.update_progress(100)

        except Exception as e:
            self.output_lines.append(f"Exception: {e}")
            if len(self.output_lines) > self.max_log_lines:
                self.output_lines = self.output_lines[-self.max_log_lines:]
            self.append_log(f"Exception: {e}")
            self.update_status("异常", "red")
            self.update_progress(100)

        finally:
            # 完成/失败后：从中间移除 + 刷新右侧已安装列表
            self.app.root.after(0, self.frame.destroy)
            self.app.load_installed_packages()

    def append_log(self, line: str):
        """线程安全地把日志追加到 Text，并保持滚动到底部。"""
        def _ui():
            self.log_text.config(state="normal")
            self.log_text.insert("end", line + "\n")

            # 只保留最后 max_log_lines 行（界面里也裁剪）
            current_lines = int(self.log_text.index("end-1c").split(".")[0])
            extra = current_lines - self.max_log_lines
            if extra > 0:
                self.log_text.delete("1.0", f"{extra + 1}.0")

            self.log_text.see("end")
            self.log_text.config(state="disabled")

        self.app.root.after(0, _ui)

    def simulate_progress(self, line):
        l = line.lower()
        if "downloading" in l:
            self.progress_value += 8
        elif "pouring" in l or "installing" in l:
            self.progress_value += 12
        elif "fetch" in l:
            self.progress_value += 6
        else:
            self.progress_value += 2

        self.progress_value = min(self.progress_value, 95)
        self.update_progress(self.progress_value)

    def update_progress(self, value):
        self.app.root.after(0, lambda: self.progress.config(value=value))

    def update_status(self, text, color):
        self.app.root.after(0, lambda: self.status.config(text=text, fg=color))


# ==============================
# 主应用
# ==============================
class BrewApp:
    def __init__(self, root):
        self.root = root
        self.root.title("BrewGUI")

        self.tasks = []
        self.all_packages = []
        self.create_ui()
        self.load_all_packages()
        self.load_installed_packages()

    # --------------------------
    # UI 构建
    # --------------------------
    def create_ui(self):
        main_frame = tk.Frame(self.root)
        main_frame.pack(fill="both", expand=True)

        # 三列
        self.left_frame = tk.Frame(main_frame, width=350)
        self.left_frame.pack(side="left", fill="y", padx=6, pady=6)

        self.center_frame = tk.Frame(main_frame, width=500)
        self.center_frame.pack(side="left", fill="both", expand=True, padx=6, pady=6)

        self.right_frame = tk.Frame(main_frame, width=350)
        self.right_frame.pack(side="left", fill="y", padx=6, pady=6)

        # 左列：搜索/推荐
        tk.Label(self.left_frame, text="搜索 / 推荐", font=("Arial", 12, "bold")).pack(anchor="w")
        self.search_entry = tk.Entry(self.left_frame)
        self.search_entry.pack(fill="x", pady=6)
        tk.Button(self.left_frame, text="搜索", command=self.search_packages).pack(pady=2)

        self.left_listbox = tk.Listbox(self.left_frame)
        self.left_listbox.pack(fill="both", expand=True, pady=6)
        self.left_listbox.bind("<Double-Button-1>", lambda e: self.show_info(self.left_listbox))

        tk.Button(self.left_frame, text="安装选中", command=self.install_left_selected).pack(pady=6)

        # 中列：正在下载（任务卡片）
        tk.Label(self.center_frame, text="正在下载", font=("Arial", 12, "bold")).pack(anchor="w")

        # Canvas + Scrollbar：可滚动任务区
        self.center_canvas = tk.Canvas(self.center_frame, highlightthickness=0)
        self.center_canvas.pack(side="left", fill="both", expand=True)

        self.center_scrollbar = ttk.Scrollbar(self.center_frame, orient="vertical", command=self.center_canvas.yview)
        self.center_scrollbar.pack(side="right", fill="y")

        self.center_canvas.configure(yscrollcommand=self.center_scrollbar.set)

        self.center_tasks_container = tk.Frame(self.center_canvas)
        self.center_window_id = self.center_canvas.create_window(
            (0, 0), window=self.center_tasks_container, anchor="nw"
        )

        def _on_container_configure(event):
            self.center_canvas.configure(scrollregion=self.center_canvas.bbox("all"))

        def _on_canvas_configure(event):
            self.center_canvas.itemconfigure(self.center_window_id, width=event.width)

        self.center_tasks_container.bind("<Configure>", _on_container_configure)
        self.center_canvas.bind("<Configure>", _on_canvas_configure)

        # 右列：已安装
        tk.Label(self.right_frame, text="已安装软件", font=("Arial", 12, "bold")).pack(anchor="w")

        self.right_listbox = tk.Listbox(self.right_frame)
        self.right_listbox.pack(fill="both", expand=True, pady=6)
        self.right_listbox.bind("<Double-Button-1>", lambda e: self.show_info(self.right_listbox))

        btn_row = tk.Frame(self.right_frame)
        btn_row.pack(fill="x", pady=4)

        tk.Button(btn_row, text="卸载选中", command=self.uninstall_selected).pack(
            side="left", expand=True, fill="x", padx=2
        )
        tk.Button(btn_row, text="更新选中", command=self.update_selected).pack(
            side="left", expand=True, fill="x", padx=2
        )

        tk.Button(self.right_frame, text="刷新已安装列表", command=self.load_installed_packages).pack(
            fill="x", pady=4
        )

    # --------------------------
    # 后台线程执行
    # --------------------------
    def run_in_thread(self, func):
        threading.Thread(target=func, daemon=True).start()

    # --------------------------
    # 加载软件列表
    # --------------------------
    def load_all_packages(self):
        def task():
            try:
                formulae = subprocess.check_output("brew formulae", shell=True, text=True).splitlines()
                casks = subprocess.check_output("brew casks", shell=True, text=True).splitlines()
                self.all_packages = formulae + casks
                self.root.after(0, self.show_recommendations)
            except Exception as e:
                self.root.after(0, lambda: messagebox.showerror("错误", str(e)))
                self.all_packages = []

        self.run_in_thread(task)

    def show_recommendations(self):
        self.left_listbox.delete(0, tk.END)
        if self.all_packages:
            recommendations = random.sample(self.all_packages, min(20, len(self.all_packages)))
            for pkg in recommendations:
                self.left_listbox.insert(tk.END, pkg)

    def search_packages(self):
        keyword = self.search_entry.get().strip()
        if not keyword:
            self.show_recommendations()
            return

        def task():
            try:
                result = subprocess.check_output(f"brew search {keyword}", shell=True, text=True)
                packages = result.splitlines()
                self.root.after(0, lambda: self._fill_left_list(packages))
            except Exception as e:
                self.root.after(0, lambda: messagebox.showerror("错误", str(e)))

        self.run_in_thread(task)

    def _fill_left_list(self, packages):
        self.left_listbox.delete(0, tk.END)
        for pkg in packages:
            if pkg.strip():
                self.left_listbox.insert(tk.END, pkg.strip())

    # --------------------------
    # 安装选中软件
    # --------------------------
    def install_left_selected(self):
        try:
            index = self.left_listbox.curselection()[0]
            package = self.left_listbox.get(index)
        except IndexError:
            messagebox.showwarning("提示", "请选择软件")
            return

        # 防止重复安装（可选）
        for t in self.tasks:
            if getattr(t, "package", None) == package and t.thread and t.thread.is_alive():
                messagebox.showinfo("提示", f"{package} 正在安装中")
                return

        task = InstallTask(self, package, self.center_tasks_container)
        task.start()
        self.tasks.append(task)

    # --------------------------
    # 已安装软件
    # --------------------------
    def load_installed_packages(self):
        def task():
            try:
                result = subprocess.check_output("brew list", shell=True, text=True)
                installed = result.splitlines()
                self.root.after(0, lambda: self._fill_right_list(installed))
            except Exception as e:
                self.root.after(0, lambda: messagebox.showerror("错误", str(e)))

        self.run_in_thread(task)

    def _fill_right_list(self, installed):
        self.right_listbox.delete(0, tk.END)
        for pkg in installed:
            if pkg.strip():
                self.right_listbox.insert(tk.END, pkg.strip())

    def uninstall_selected(self):
        try:
            index = self.right_listbox.curselection()[0]
            package = self.right_listbox.get(index)
        except IndexError:
            messagebox.showwarning("提示", "请选择软件")
            return

        if not messagebox.askyesno("确认", f"确定卸载 {package} 吗？"):
            return

        def task():
            subprocess.call(f"brew uninstall {package}", shell=True)
            self.load_installed_packages()

        self.run_in_thread(task)

    def update_selected(self):
        try:
            index = self.right_listbox.curselection()[0]
            package = self.right_listbox.get(index)
        except IndexError:
            messagebox.showwarning("提示", "请选择软件")
            return

        def task():
            subprocess.call(f"brew upgrade {package}", shell=True)
            self.load_installed_packages()

        self.run_in_thread(task)

    # --------------------------
    # brew info 美化显示
    # --------------------------
    def parse_brew_info(self, raw: str):
        lines = raw.splitlines()
        summary = []
        sections = {}
        current = None

        for line in lines:
            if line.startswith("==>"):
                title = line.replace("==>", "").strip()
                current = title if title else "Other"
                sections.setdefault(current, [])
            else:
                if current is None:
                    if line.strip():
                        summary.append(line)
                else:
                    sections[current].append(line)

        return summary, sections

    def show_info_window(self, package: str, raw: str):
        summary, sections = self.parse_brew_info(raw)

        win = tk.Toplevel(self.root)
        win.title(f"软件信息 - {package}")
        win.geometry("780x520")
        win.minsize(680, 420)

        style = ttk.Style(win)
        try:
            style.configure("Card.TLabelframe", padding=10)
            style.configure("Card.TLabelframe.Label", font=("Arial", 12, "bold"))
        except tk.TclError:
            pass

        header = tk.Frame(win, padx=12, pady=10)
        header.pack(fill="x")

        tk.Label(header, text=package, font=("Arial", 16, "bold")).pack(side="left")

        btns = tk.Frame(header)
        btns.pack(side="right")

        def copy_all():
            self.root.clipboard_clear()
            self.root.clipboard_append(raw)

        ttk.Button(btns, text="复制全部", command=copy_all).pack(side="left", padx=4)
        ttk.Button(btns, text="关闭", command=win.destroy).pack(side="left", padx=4)

        outer = tk.Frame(win)
        outer.pack(fill="both", expand=True, padx=12, pady=(0, 12))

        canvas = tk.Canvas(outer, highlightthickness=0)
        canvas.pack(side="left", fill="both", expand=True)

        scrollbar = ttk.Scrollbar(outer, orient="vertical", command=canvas.yview)
        scrollbar.pack(side="right", fill="y")
        canvas.configure(yscrollcommand=scrollbar.set)

        content = tk.Frame(canvas)
        window_id = canvas.create_window((0, 0), window=content, anchor="nw")

        def _on_content_configure(event):
            canvas.configure(scrollregion=canvas.bbox("all"))

        def _on_canvas_configure(event):
            canvas.itemconfigure(window_id, width=event.width)

        content.bind("<Configure>", _on_content_configure)
        canvas.bind("<Configure>", _on_canvas_configure)

        def _on_mousewheel(e):
            if e.delta:
                canvas.yview_scroll(int(-1 * (e.delta / 120)), "units")
            else:
                if e.num == 4:
                    canvas.yview_scroll(-3, "units")
                elif e.num == 5:
                    canvas.yview_scroll(3, "units")

        win.bind_all("<MouseWheel>", _on_mousewheel)
        win.bind_all("<Button-4>", _on_mousewheel)
        win.bind_all("<Button-5>", _on_mousewheel)

        def add_block(title_text: str, body_lines):
            lf = ttk.LabelFrame(content, text=title_text, style="Card.TLabelframe")
            lf.pack(fill="x", pady=8)

            body = "\n".join(body_lines).strip() if body_lines else "(空)"
            txt = tk.Text(
                lf,
                height=min(max(len(body_lines), 2), 12),
                wrap="word",
                font=("Menlo", 12),
                relief="flat",
                bg=win.cget("bg"),
            )
            txt.pack(fill="x")
            txt.insert("1.0", body)
            txt.config(state="disabled")

        if summary:
            add_block("Summary", summary)

        header_sections = [k for k in sections.keys() if ":" in k]
        for k in header_sections:
            add_block(k, [ln for ln in sections[k] if ln.strip()])

        for k in ["Names", "Description", "Artifacts", "Analytics"]:
            if k in sections:
                add_block(k, [ln for ln in sections[k] if ln.strip()])

        for k, v in sections.items():
            if (k in header_sections) or (k in ["Names", "Description", "Artifacts", "Analytics"]):
                continue
            if v and any(ln.strip() for ln in v):
                add_block(k, [ln for ln in v if ln.strip()])

    # --------------------------
    # 显示软件信息（双击）
    # --------------------------
    def show_info(self, listbox):
        try:
            index = listbox.curselection()[0]
            package = listbox.get(index)
        except IndexError:
            return

        def task():
            try:
                result = subprocess.check_output(f"brew info {package}", shell=True, text=True)
                self.root.after(0, lambda: self.show_info_window(package, result))
            except Exception as e:
                self.root.after(0, lambda: messagebox.showerror("错误", str(e)))

        self.run_in_thread(task)


def run_app():
    root = tk.Tk()

    # ✅ 启动时就居中（无“先出现再移动”的跳动）
    root.withdraw()
    width, height = 800, 600
    screen_w = root.winfo_screenwidth()
    screen_h = root.winfo_screenheight()
    x = (screen_w - width) // 2
    y = (screen_h - height) // 2
    root.geometry(f"{width}x{height}+{x}+{y}")

    BrewApp(root)

    root.deiconify()
    root.mainloop()


if __name__ == '__main__':
    run_app()
