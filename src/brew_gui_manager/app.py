from __future__ import annotations

import tkinter as tk
from tkinter import messagebox
from tkinter import ttk
from typing import Callable

from .brew_service import BrewCommandResult, BrewService, BrewSnapshot, PackageDetails
from .task_runner import BackgroundTaskRunner, TaskEvent
from .ui_state import PackageSelection


class BrewManagerApp:
    def __init__(self, root: tk.Tk, service: BrewService | None = None) -> None:
        self.root = root
        self.service = service or BrewService()
        self.root.title("Brew GUI Manager")
        self.root.geometry("1380x860")
        self.root.minsize(1180, 720)
        self.root.configure(bg="#f4f6fb")
        self.root.update_idletasks()
        self.root.deiconify()
        self.root.lift()

        self.status_var = tk.StringVar(value="Connecting to Homebrew...")
        self.error_var = tk.StringVar(value="")
        self.filter_var = tk.StringVar(value="")
        self.install_name_var = tk.StringVar(value="")
        self.install_kind_var = tk.StringVar(value="formula")
        self.selection_var = tk.StringVar(value="Choose a package to see details.")
        self.package_blurb_var = tk.StringVar(value="Select a package to see its story.")
        self.package_meta_var = tk.StringVar(value="Latest version: -    Installed: -")
        self.summary_var = tk.StringVar(value="Formulae 0  •  Casks 0")
        self.badge_var = tk.StringVar(value="No updates available")
        self.hero_var = tk.StringVar(value="Your Homebrew apps, curated like a storefront.")
        self.category_var = tk.StringVar(value="all")
        self.activity_var = tk.StringVar(value="Idle")

        self._all_formulae: list[str] = []
        self._all_casks: list[str] = []
        self._outdated_formulae: list[str] = []
        self._outdated_casks: list[str] = []
        self._selected_package: PackageSelection | None = None
        self._task_runner = BackgroundTaskRunner()
        self._task_handlers: dict[int, tuple[Callable[[object], None] | None, Callable[[Exception], None] | None]] = {}
        self._active_tasks: set[int] = set()
        self._action_buttons: list[ttk.Button] = []

        self._configure_styles()
        self._build_layout()
        self.filter_var.trace_add("write", lambda *_: self._apply_filter())
        self.root.after(50, self.refresh)
        self.root.after(120, self._poll_task_events)

    def _configure_styles(self) -> None:
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("App.TFrame", background="#f4f6fb")
        style.configure("Sidebar.TFrame", background="#eef2ff")
        style.configure("Card.TFrame", background="#ffffff")
        style.configure("SoftCard.TFrame", background="#f8fafc")
        style.configure(
            "Hero.TFrame",
            background="#0f172a",
        )
        style.configure(
            "Title.TLabel",
            background="#f4f6fb",
            foreground="#0f172a",
            font=("SF Pro Display", 28, "bold"),
        )
        style.configure(
            "Section.TLabel",
            background="#ffffff",
            foreground="#0f172a",
            font=("SF Pro Display", 18, "bold"),
        )
        style.configure(
            "HeroTitle.TLabel",
            background="#0f172a",
            foreground="#f8fafc",
            font=("SF Pro Display", 30, "bold"),
        )
        style.configure(
            "HeroBody.TLabel",
            background="#0f172a",
            foreground="#cbd5e1",
            font=("SF Pro Text", 12),
        )
        style.configure(
            "Muted.TLabel",
            background="#ffffff",
            foreground="#64748b",
            font=("SF Pro Text", 11),
        )
        style.configure(
            "SidebarTitle.TLabel",
            background="#eef2ff",
            foreground="#334155",
            font=("SF Pro Text", 12, "bold"),
        )
        style.configure(
            "Sidebar.TButton",
            background="#eef2ff",
            foreground="#1e293b",
            borderwidth=0,
            font=("SF Pro Text", 11),
            padding=(16, 10),
        )
        style.map(
            "Sidebar.TButton",
            background=[("active", "#dbeafe"), ("pressed", "#bfdbfe")],
        )
        style.configure(
            "Primary.TButton",
            background="#2563eb",
            foreground="#ffffff",
            borderwidth=0,
            padding=(16, 10),
            font=("SF Pro Text", 11, "bold"),
        )
        style.map(
            "Primary.TButton",
            background=[("active", "#1d4ed8"), ("pressed", "#1e40af")],
        )
        style.configure(
            "Secondary.TButton",
            background="#e2e8f0",
            foreground="#0f172a",
            borderwidth=0,
            padding=(14, 10),
            font=("SF Pro Text", 11, "bold"),
        )
        style.map(
            "Secondary.TButton",
            background=[("active", "#cbd5e1"), ("pressed", "#94a3b8")],
        )
        style.configure(
            "Category.TButton",
            background="#ffffff",
            foreground="#0f172a",
            borderwidth=0,
            padding=(14, 12),
            font=("SF Pro Text", 11, "bold"),
        )
        style.map(
            "Category.TButton",
            background=[("active", "#dbeafe"), ("pressed", "#bfdbfe")],
        )

    def _build_layout(self) -> None:
        shell = ttk.Frame(self.root, style="App.TFrame", padding=20)
        shell.pack(fill=tk.BOTH, expand=True)
        shell.columnconfigure(1, weight=1)
        shell.rowconfigure(0, weight=1)

        sidebar = ttk.Frame(shell, style="Sidebar.TFrame", padding=18)
        sidebar.grid(row=0, column=0, sticky="nsw", padx=(0, 18))
        sidebar.configure(width=220)
        sidebar.grid_propagate(False)
        self._build_sidebar(sidebar)

        content = ttk.Frame(shell, style="App.TFrame")
        content.grid(row=0, column=1, sticky="nsew")
        content.columnconfigure(0, weight=1)
        content.rowconfigure(2, weight=1)

        header = ttk.Frame(content, style="App.TFrame")
        header.grid(row=0, column=0, sticky="ew")
        header.columnconfigure(0, weight=1)
        ttk.Label(header, text="Brew Store", style="Title.TLabel").grid(
            row=0,
            column=0,
            sticky="w",
        )
        ttk.Label(
            header,
            text="A Homebrew control center styled like an app marketplace.",
            style="Muted.TLabel",
        ).grid(row=1, column=0, sticky="w", pady=(4, 0))
        ttk.Label(
            header,
            textvariable=self.activity_var,
            style="Muted.TLabel",
        ).grid(row=0, column=1, sticky="e")

        self._build_hero(content)
        self._build_storefront(content)

    def _build_sidebar(self, parent: ttk.Frame) -> None:
        ttk.Label(parent, text="Library", style="SidebarTitle.TLabel").pack(anchor="w")
        ttk.Label(
            parent,
            text="Browse packages by collection and manage installs quickly.",
            style="SidebarTitle.TLabel",
            wraplength=180,
        ).pack(anchor="w", pady=(8, 18))

        nav_items = [
            ("All Apps", "all"),
            ("Formulae", "formula"),
            ("Casks", "cask"),
            ("Updates", "outdated"),
        ]
        for label, value in nav_items:
            ttk.Button(
                parent,
                text=label,
                style="Sidebar.TButton",
                command=lambda selected=value: self._set_category(selected),
            ).pack(fill=tk.X, pady=4)

        install_card = ttk.Frame(parent, style="Card.TFrame", padding=14)
        install_card.pack(fill=tk.X, pady=(22, 0))
        ttk.Label(install_card, text="Quick Install", style="Section.TLabel").pack(anchor="w")
        ttk.Label(
            install_card,
            text="Drop in any formula or cask and add it to your shelf.",
            style="Muted.TLabel",
            wraplength=170,
        ).pack(anchor="w", pady=(4, 12))
        install_entry = ttk.Entry(install_card, textvariable=self.install_name_var)
        install_entry.pack(fill=tk.X)
        kind_box = ttk.Combobox(
            install_card,
            textvariable=self.install_kind_var,
            values=("formula", "cask"),
            state="readonly",
        )
        kind_box.pack(fill=tk.X, pady=(10, 10))
        install_button = ttk.Button(
            install_card,
            text="Install Package",
            style="Primary.TButton",
            command=self._install_package,
        )
        install_button.pack(fill=tk.X)
        self._register_action_button(install_button)

        stats_card = ttk.Frame(parent, style="SoftCard.TFrame", padding=14)
        stats_card.pack(fill=tk.X, pady=(18, 0))
        ttk.Label(stats_card, text="System Status", style="SidebarTitle.TLabel").pack(anchor="w")
        ttk.Label(
            stats_card,
            textvariable=self.status_var,
            background="#f8fafc",
            foreground="#0f172a",
            wraplength=170,
            justify="left",
            font=("SF Pro Text", 11, "bold"),
        ).pack(anchor="w", pady=(8, 6))
        ttk.Label(
            stats_card,
            textvariable=self.error_var,
            background="#f8fafc",
            foreground="#b45309",
            wraplength=170,
            justify="left",
            font=("SF Pro Text", 10),
        ).pack(anchor="w")

    def _build_hero(self, parent: ttk.Frame) -> None:
        hero = ttk.Frame(parent, style="Hero.TFrame", padding=22)
        hero.grid(row=1, column=0, sticky="ew", pady=(18, 20))
        hero.columnconfigure(0, weight=1)
        hero.columnconfigure(1, weight=1)

        left = ttk.Frame(hero, style="Hero.TFrame")
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 20))
        ttk.Label(left, text="Featured Collection", style="HeroTitle.TLabel").pack(anchor="w")
        ttk.Label(
            left,
            textvariable=self.hero_var,
            style="HeroBody.TLabel",
            wraplength=460,
            justify="left",
        ).pack(anchor="w", pady=(12, 18))

        controls = ttk.Frame(left, style="Hero.TFrame")
        controls.pack(anchor="w")
        ttk.Entry(controls, textvariable=self.filter_var, width=34).grid(row=0, column=0, padx=(0, 10))
        refresh_button = ttk.Button(controls, text="Refresh", style="Primary.TButton", command=self.refresh)
        refresh_button.grid(
            row=0,
            column=1,
        )
        self._register_action_button(refresh_button)
        upgrade_all_button = ttk.Button(
            controls,
            text="Upgrade All",
            style="Secondary.TButton",
            command=self._upgrade_all,
        )
        upgrade_all_button.grid(row=0, column=2, padx=(10, 0))
        self._register_action_button(upgrade_all_button)

        right = ttk.Frame(hero, style="Hero.TFrame")
        right.grid(row=0, column=1, sticky="nsew")
        self._build_metric_card(right, "Installed", self.summary_var, 0)
        self._build_metric_card(right, "Updates", self.badge_var, 1)

    def _build_metric_card(
        self,
        parent: ttk.Frame,
        title: str,
        variable: tk.StringVar,
        column: int,
    ) -> None:
        card = tk.Frame(parent, bg="#172554", padx=18, pady=18)
        card.grid(row=0, column=column, sticky="nsew", padx=(0 if column == 0 else 12, 0))
        ttk.Label(
            card,
            text=title,
            background="#172554",
            foreground="#bfdbfe",
            font=("SF Pro Text", 11, "bold"),
        ).pack(anchor="w")
        ttk.Label(
            card,
            textvariable=variable,
            background="#172554",
            foreground="#eff6ff",
            font=("SF Pro Display", 16, "bold"),
            wraplength=180,
            justify="left",
        ).pack(anchor="w", pady=(10, 0))

    def _build_storefront(self, parent: ttk.Frame) -> None:
        storefront = ttk.Frame(parent, style="App.TFrame")
        storefront.grid(row=2, column=0, sticky="nsew")
        storefront.columnconfigure(0, weight=3)
        storefront.columnconfigure(1, weight=2)
        storefront.rowconfigure(0, weight=1)

        shelves = ttk.Frame(storefront, style="App.TFrame")
        shelves.grid(row=0, column=0, sticky="nsew", padx=(0, 18))
        shelves.columnconfigure(0, weight=1)
        shelves.columnconfigure(1, weight=1)
        shelves.rowconfigure(1, weight=1)

        ttk.Label(
            shelves,
            text="Top Charts",
            style="Title.TLabel",
        ).grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 10))

        self.formulae_list = self._build_shelf(shelves, "Formulae", 1, 0, "formula")
        self.casks_list = self._build_shelf(shelves, "Casks", 1, 1, "cask")

        details = ttk.Frame(storefront, style="Card.TFrame", padding=20)
        details.grid(row=0, column=1, sticky="nsew")
        details.columnconfigure(0, weight=1)
        details.rowconfigure(6, weight=1)
        details.rowconfigure(8, weight=1)

        ttk.Label(details, text="App Page", style="Section.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Label(
            details,
            textvariable=self.selection_var,
            background="#ffffff",
            foreground="#0f172a",
            font=("SF Pro Display", 20, "bold"),
            wraplength=420,
            justify="left",
        ).grid(row=1, column=0, sticky="w", pady=(8, 4))
        ttk.Label(
            details,
            textvariable=self.package_blurb_var,
            background="#ffffff",
            foreground="#475569",
            font=("SF Pro Text", 12),
            wraplength=420,
            justify="left",
        ).grid(row=2, column=0, sticky="w")
        ttk.Label(
            details,
            textvariable=self.package_meta_var,
            background="#ffffff",
            foreground="#2563eb",
            font=("SF Pro Text", 11, "bold"),
            wraplength=420,
            justify="left",
        ).grid(row=3, column=0, sticky="w", pady=(8, 0))

        actions = ttk.Frame(details, style="Card.TFrame")
        actions.grid(row=4, column=0, sticky="w", pady=(18, 16))
        details_button = ttk.Button(actions, text="Open Details", style="Primary.TButton", command=self._show_selected_details)
        details_button.grid(
            row=0,
            column=0,
        )
        self._register_action_button(details_button)
        upgrade_selected_button = ttk.Button(
            actions,
            text="Upgrade Selected",
            style="Secondary.TButton",
            command=self._upgrade_selected,
        )
        upgrade_selected_button.grid(row=0, column=1, padx=(10, 0))
        self._register_action_button(upgrade_selected_button)
        uninstall_button = ttk.Button(
            actions,
            text="Uninstall",
            style="Secondary.TButton",
            command=self._uninstall_selected,
        )
        uninstall_button.grid(row=0, column=2, padx=(10, 0))
        self._register_action_button(uninstall_button)
        cleanup_button = ttk.Button(
            actions,
            text="Cleanup",
            style="Secondary.TButton",
            command=self._cleanup,
        )
        cleanup_button.grid(row=0, column=3, padx=(10, 0))
        self._register_action_button(cleanup_button)

        ttk.Label(details, text="About This Package", style="Section.TLabel").grid(
            row=5,
            column=0,
            sticky="nw",
            pady=(0, 10),
        )
        self.details_text = tk.Text(
            details,
            wrap="word",
            height=14,
            relief=tk.FLAT,
            bg="#f8fafc",
            fg="#0f172a",
            font=("SF Pro Text", 11),
            padx=16,
            pady=16,
        )
        self.details_text.grid(row=6, column=0, sticky="nsew")
        self._set_text(
            self.details_text,
            "Select an app from the charts to load its Homebrew detail page.",
        )

        ttk.Label(details, text="Recent Activity", style="Section.TLabel").grid(
            row=7,
            column=0,
            sticky="w",
            pady=(16, 10),
        )
        self.log_text = tk.Text(
            details,
            wrap="word",
            height=10,
            relief=tk.FLAT,
            bg="#0f172a",
            fg="#e2e8f0",
            font=("SF Mono", 10),
            padx=16,
            pady=16,
        )
        self.log_text.grid(row=8, column=0, sticky="nsew")
        self._append_log("Storefront ready. Refresh to sync with Homebrew.")

    def _build_shelf(
        self,
        parent: ttk.Frame,
        title: str,
        row: int,
        column: int,
        package_kind: str,
    ) -> tk.Listbox:
        card = ttk.Frame(parent, style="Card.TFrame", padding=16)
        card.grid(row=row, column=column, sticky="nsew", padx=(0 if column == 0 else 10, 0))
        card.columnconfigure(0, weight=1)
        card.rowconfigure(2, weight=1)

        ttk.Label(card, text=title, style="Section.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Label(
            card,
            text="Browse installed packages like a ranked collection.",
            style="Muted.TLabel",
        ).grid(row=1, column=0, sticky="w", pady=(4, 10))

        frame = tk.Frame(card, bg="#ffffff")
        frame.grid(row=2, column=0, sticky="nsew")
        frame.grid_columnconfigure(0, weight=1)
        frame.grid_rowconfigure(0, weight=1)

        listbox = tk.Listbox(
            frame,
            activestyle="none",
            relief=tk.FLAT,
            bg="#ffffff",
            fg="#0f172a",
            selectbackground="#bfdbfe",
            selectforeground="#0f172a",
            font=("SF Pro Text", 12),
            highlightthickness=0,
            bd=0,
        )
        scrollbar = ttk.Scrollbar(frame, orient=tk.VERTICAL, command=listbox.yview)
        listbox.configure(yscrollcommand=scrollbar.set)
        listbox.bind("<<ListboxSelect>>", lambda _event: self._handle_selection(listbox, package_kind))
        listbox.grid(row=0, column=0, sticky="nsew")
        scrollbar.grid(row=0, column=1, sticky="ns")
        return listbox

    def refresh(self) -> None:
        self._submit_task(
            description="Refreshing storefront",
            fn=self.service.collect_snapshot,
            on_success=lambda payload: self._render_snapshot(payload),
        )

    def _render_snapshot(self, snapshot: BrewSnapshot) -> None:
        if snapshot.available:
            self.status_var.set(snapshot.version)
            self.summary_var.set(f"Formulae {len(snapshot.formulae)}  •  Casks {len(snapshot.casks)}")
            update_count = len(snapshot.outdated_formulae) + len(snapshot.outdated_casks)
            self.badge_var.set(f"{update_count} package updates waiting")
            if update_count:
                self.hero_var.set(
                    "Updates are ready. Open a package page, inspect details, or upgrade the whole library."
                )
            else:
                self.hero_var.set("Your Homebrew library is up to date and ready to browse.")
        else:
            self.status_var.set("Homebrew unavailable")
            self.summary_var.set("Formulae 0  •  Casks 0")
            self.badge_var.set("Install Homebrew to unlock the catalog")
            self.hero_var.set("Homebrew is missing from PATH, so the storefront cannot load your library yet.")

        self.error_var.set(snapshot.error)
        self._all_formulae = snapshot.formulae
        self._all_casks = snapshot.casks
        self._outdated_formulae = snapshot.outdated_formulae
        self._outdated_casks = snapshot.outdated_casks
        self._apply_filter()

    def _apply_filter(self) -> None:
        keyword = self.filter_var.get().strip().lower()
        category = self.category_var.get()

        formulae_source = self._outdated_formulae if category == "outdated" else self._all_formulae
        casks_source = self._outdated_casks if category == "outdated" else self._all_casks

        formulae = self._filter_items(formulae_source, keyword)
        casks = self._filter_items(casks_source, keyword)

        if category == "formula":
            casks = []
        elif category == "cask":
            formulae = []

        self._replace_listbox(self.formulae_list, formulae)
        self._replace_listbox(self.casks_list, casks)

    def _set_category(self, category: str) -> None:
        self.category_var.set(category)
        self._append_log(f"Browsing category: {category}")
        self._apply_filter()

    @staticmethod
    def _filter_items(items: list[str], keyword: str) -> list[str]:
        if not keyword:
            return items
        return [item for item in items if keyword in item.lower()]

    @staticmethod
    def _replace_listbox(listbox: tk.Listbox, items: list[str]) -> None:
        listbox.delete(0, tk.END)
        for index, item in enumerate(items, start=1):
            listbox.insert(tk.END, f"{index:02d}   {item}")

    def _handle_selection(self, listbox: tk.Listbox, package_kind: str) -> None:
        selection = listbox.curselection()
        if not selection:
            return

        raw_item = listbox.get(selection[0])
        name = raw_item.split(maxsplit=1)[1] if " " in raw_item else raw_item
        self._selected_package = PackageSelection(name=name, kind=package_kind)
        self.selection_var.set(f"{name}  •  {package_kind}")
        self.package_blurb_var.set("Open Details to load the package overview from Homebrew.")
        self.package_meta_var.set("Latest version: -    Installed: -")
        self._set_text(
            self.details_text,
            f"{name}\n\nOpen Details to load the package overview from Homebrew.",
        )

    def _show_selected_details(self) -> None:
        if self._selected_package is None:
            self._append_log("No package selected for details.")
            return

        selection = self._selected_package
        self._submit_task(
            description=f"Loading details for {selection.name}",
            fn=lambda: self.service.get_package_details(selection.name, selection.kind),
            on_success=lambda payload: self._handle_details_loaded(selection, payload),
        )

    def _install_package(self) -> None:
        package_name = self.install_name_var.get().strip()
        package_kind = self.install_kind_var.get()
        action = "install_cask" if package_kind == "cask" else "install_formula"
        self._run_and_refresh(action, package_name=package_name, package_kind=package_kind)
        if self.error_var.get() == "":
            self.install_name_var.set("")

    def _upgrade_all(self) -> None:
        self._run_and_refresh("upgrade_all")

    def _cleanup(self) -> None:
        if not messagebox.askyesno("Confirm Cleanup", "Run `brew cleanup` now?"):
            return
        self._run_and_refresh("cleanup")

    def _upgrade_selected(self) -> None:
        if self._selected_package is None:
            self._append_log("No package selected for upgrade.")
            return
        self._run_and_refresh(
            "upgrade_selected",
            package_name=self._selected_package.name,
            package_kind=self._selected_package.kind,
        )

    def _uninstall_selected(self) -> None:
        if self._selected_package is None:
            self._append_log("No package selected for uninstall.")
            return

        confirmed = messagebox.askyesno(
            "Confirm Uninstall",
            f"Uninstall {self._selected_package.name}?",
        )
        if not confirmed:
            return

        action = (
            "uninstall_cask"
            if self._selected_package.kind == "cask"
            else "uninstall_formula"
        )
        self._run_and_refresh(
            action,
            package_name=self._selected_package.name,
            package_kind=self._selected_package.kind,
        )

    def _run_and_refresh(
        self,
        action: str,
        package_name: str = "",
        package_kind: str = "formula",
    ) -> None:
        self._submit_task(
            description=f"Running {action}",
            fn=lambda: self.service.run_action(
                action,
                package_name=package_name,
                package_kind=package_kind,
            ),
            on_success=lambda payload: self._handle_action_result(payload),
        )

    def _handle_command_result(self, result: BrewCommandResult) -> None:
        command_text = " ".join(result.command) if result.command else "<no command>"
        if result.succeeded:
            self.error_var.set("")
            message = result.output or "Command completed successfully."
            self._append_log(f"$ {command_text}\n{message}")
            return

        self.error_var.set(result.error)
        self._append_log(f"$ {command_text}\nERROR: {result.error}")

    @staticmethod
    def _set_text(widget: tk.Text, content: str) -> None:
        widget.delete("1.0", tk.END)
        widget.insert("1.0", content)

    def _append_log(self, content: str) -> None:
        self.log_text.insert(tk.END, f"{content}\n\n")
        self.log_text.see(tk.END)

    def _handle_details_loaded(self, selection: PackageSelection, details: object) -> None:
        if not isinstance(details, PackageDetails):
            self.error_var.set("Unexpected package details payload received.")
            self._append_log("ERROR: Unexpected package details payload received.")
            return

        self.selection_var.set(f"{details.title}  •  {selection.kind}")
        self.package_blurb_var.set(details.description)
        installed = ", ".join(details.installed_versions) if details.installed_versions else "Not installed"
        self.package_meta_var.set(
            f"Latest version: {details.latest_version}    Installed: {installed}"
        )
        self._set_text(self.details_text, self._format_package_details(details))
        self._append_log(f"Loaded details for {selection.name} ({selection.kind}).")

    def _handle_action_result(self, payload: object) -> None:
        result = payload
        if not isinstance(result, BrewCommandResult):
            self.error_var.set("Unexpected action result received.")
            self._append_log("ERROR: Unexpected action result received.")
            return

        self._handle_command_result(result)
        if result.succeeded:
            self.refresh()

    def _submit_task(
        self,
        description: str,
        fn: Callable[[], object],
        on_success: Callable[[object], None] | None = None,
        on_error: Callable[[Exception], None] | None = None,
    ) -> None:
        task_id = self._task_runner.submit(description, fn)
        self._task_handlers[task_id] = (on_success, on_error)

    def _poll_task_events(self) -> None:
        for event in self._task_runner.drain_events():
            self._handle_task_event(event)
        self.root.after(120, self._poll_task_events)

    def _handle_task_event(self, event: TaskEvent) -> None:
        handlers = self._task_handlers.get(event.task_id, (None, None))
        on_success, on_error = handlers

        if event.status == "started":
            self._active_tasks.add(event.task_id)
            self.activity_var.set(f"{event.description}...")
            self._set_busy_state(True)
            self._append_log(f"{event.description} started.")
            return

        self._active_tasks.discard(event.task_id)
        if not self._active_tasks:
            self.activity_var.set("Idle")
            self._set_busy_state(False)

        if event.status == "completed":
            if on_success is not None:
                on_success(event.payload)
            self._append_log(f"{event.description} finished.")
        elif event.status == "failed":
            error = event.error or RuntimeError("Background task failed.")
            if on_error is not None:
                on_error(error)
            else:
                self.error_var.set(str(error))
                self._append_log(f"ERROR: {event.description} failed: {error}")

        self._task_handlers.pop(event.task_id, None)

    def _set_busy_state(self, busy: bool) -> None:
        state = tk.DISABLED if busy else tk.NORMAL
        for button in self._action_buttons:
            button.configure(state=state)

    def _register_action_button(self, button: ttk.Button) -> None:
        self._action_buttons.append(button)

    @staticmethod
    def _format_package_details(details: PackageDetails) -> str:
        sections = [
            f"Name: {details.name}",
            f"Kind: {details.kind}",
            f"Homepage: {details.homepage or 'Unavailable'}",
            f"Tap: {details.tap or 'Unavailable'}",
            f"Latest version: {details.latest_version}",
            f"Installed versions: {', '.join(details.installed_versions) or 'None'}",
            f"Dependencies: {', '.join(details.dependencies) or 'None'}",
        ]
        if details.caveats:
            sections.append(f"Caveats: {details.caveats}")
        sections.append("")
        sections.append("Raw Homebrew Info")
        sections.append(details.raw_text)
        return "\n".join(sections)
