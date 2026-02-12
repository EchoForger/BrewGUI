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
        self.progress.pack(fill="x", pady=6)

        self.log_btn = tk.Button(self.frame, text="查看日志", command=self.show_log)
        self.log_btn.pack(anchor="e")

    def show_log(self):
        # 展示最近输出，避免过长
        text = "\n".join(self.output_lines[-200:]) if self.output_lines else "(暂无输出)"
        messagebox.showinfo(f"{self.package} 输出", text)

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
            self.update_status("异常", "red")
            self.update_progress(100)

        finally:
            # 完成/失败后：从中间移除 + 刷新右侧已安装列表
            self.app.root.after(0, self.frame.destroy)
            self.app.load_installed_packages()

    def simulate_progress(self, line):
        # 仅用于“估算进度”，brew 输出不稳定，所以做轻量模拟
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
        self.root.title("PyBrew 三列版")
        self.root.geometry("1200x600")
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

        # 用 Canvas + Scrollbar 做可滚动任务区
        self.center_canvas = tk.Canvas(self.center_frame, highlightthickness=0)
        self.center_canvas.pack(side="left", fill="both", expand=True)

        self.center_scrollbar = tk.Scrollbar(self.center_frame, orient="vertical", command=self.center_canvas.yview)
        self.center_scrollbar.pack(side="right", fill="y")

        self.center_canvas.configure(yscrollcommand=self.center_scrollbar.set)

        self.center_tasks_container = tk.Frame(self.center_canvas)
        self.center_window_id = self.center_canvas.create_window((0, 0), window=self.center_tasks_container, anchor="nw")

        def _on_container_configure(event):
            self.center_canvas.configure(scrollregion=self.center_canvas.bbox("all"))

        def _on_canvas_configure(event):
            # 让内部 frame 宽度跟随 canvas
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

        tk.Button(btn_row, text="卸载选中", command=self.uninstall_selected).pack(side="left", expand=True, fill="x", padx=2)
        tk.Button(btn_row, text="更新选中", command=self.update_selected).pack(side="left", expand=True, fill="x", padx=2)

        tk.Button(self.right_frame, text="刷新已安装列表", command=self.load_installed_packages).pack(fill="x", pady=4)

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

        # 防止重复安装显示（可选）
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
    # 显示软件信息
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
                self.root.after(0, lambda: messagebox.showinfo(package, result))
            except Exception as e:
                self.root.after(0, lambda: messagebox.showerror("错误", str(e)))

        self.run_in_thread(task)


if __name__ == "__main__":
    root = tk.Tk()
    app = BrewApp(root)
    root.mainloop()
