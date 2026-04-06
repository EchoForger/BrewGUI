from __future__ import annotations

import tkinter as tk
from tkinter import messagebox
from tkinter import ttk

from .brew_service import BrewCommandResult, BrewService, BrewSnapshot
from .ui_state import PackageSelection


class BrewManagerApp:
    def __init__(self, root: tk.Tk, service: BrewService | None = None) -> None:
        self.root = root
        self.service = service or BrewService()
        self.root.title("Brew GUI Manager")
        self.root.geometry("920x640")
        self.root.minsize(760, 520)

        self.status_var = tk.StringVar(value="Loading Homebrew status...")
        self.error_var = tk.StringVar(value="")
        self.filter_var = tk.StringVar(value="")
        self.install_name_var = tk.StringVar(value="")
        self.install_kind_var = tk.StringVar(value="formula")
        self.selection_var = tk.StringVar(value="No package selected.")
        self.summary_var = tk.StringVar(value="Outdated formulae: 0 | Outdated casks: 0")
        self._all_formulae: list[str] = []
        self._all_casks: list[str] = []
        self._selected_package: PackageSelection | None = None

        self._build_layout()
        self.filter_var.trace_add("write", lambda *_: self._apply_filter())
        self.refresh()

    def _build_layout(self) -> None:
        container = ttk.Frame(self.root, padding=16)
        container.pack(fill=tk.BOTH, expand=True)
        container.columnconfigure(0, weight=1)
        container.rowconfigure(2, weight=1)

        header = ttk.Frame(container)
        header.grid(row=0, column=0, sticky="ew")
        header.columnconfigure(0, weight=1)

        ttk.Label(
            header,
            text="Homebrew GUI Manager",
            font=("Helvetica", 20, "bold"),
        ).grid(row=0, column=0, sticky="w")
        actions = ttk.Frame(header)
        actions.grid(row=0, column=1, sticky="e")
        ttk.Button(actions, text="Refresh", command=self.refresh).grid(row=0, column=0)
        ttk.Button(actions, text="Upgrade All", command=self._upgrade_all).grid(
            row=0,
            column=1,
            padx=(8, 0),
        )
        ttk.Button(actions, text="Cleanup", command=self._cleanup).grid(
            row=0,
            column=2,
            padx=(8, 0),
        )

        status_panel = ttk.Frame(container, padding=(0, 12, 0, 12))
        status_panel.grid(row=1, column=0, sticky="ew")
        status_panel.columnconfigure(1, weight=1)
        status_panel.columnconfigure(3, weight=1)

        ttk.Label(status_panel, text="Status:").grid(row=0, column=0, sticky="w")
        ttk.Label(status_panel, textvariable=self.status_var).grid(
            row=0,
            column=1,
            columnspan=3,
            sticky="w",
        )
        ttk.Label(status_panel, text="Filter:").grid(row=1, column=0, sticky="w")
        ttk.Entry(status_panel, textvariable=self.filter_var).grid(
            row=1,
            column=1,
            sticky="ew",
            pady=(8, 0),
        )
        ttk.Label(status_panel, text="Install:").grid(row=1, column=2, sticky="e", padx=(12, 0))
        ttk.Entry(status_panel, textvariable=self.install_name_var).grid(
            row=1,
            column=3,
            sticky="ew",
            padx=(8, 0),
            pady=(8, 0),
        )
        ttk.Combobox(
            status_panel,
            textvariable=self.install_kind_var,
            values=("formula", "cask"),
            state="readonly",
            width=10,
        ).grid(row=1, column=4, padx=(8, 0), pady=(8, 0))
        ttk.Button(status_panel, text="Install", command=self._install_package).grid(
            row=1,
            column=5,
            padx=(8, 0),
            pady=(8, 0),
        )
        ttk.Label(status_panel, textvariable=self.summary_var).grid(
            row=2,
            column=0,
            columnspan=6,
            sticky="w",
            pady=(8, 0),
        )
        ttk.Label(
            status_panel,
            textvariable=self.error_var,
            foreground="#9a3412",
        ).grid(row=3, column=0, columnspan=6, sticky="w", pady=(8, 0))

        content = ttk.Panedwindow(container, orient=tk.HORIZONTAL)
        content.grid(row=2, column=0, sticky="nsew")

        left_panel = ttk.Panedwindow(content, orient=tk.HORIZONTAL)
        self.formulae_list = self._build_list_panel(left_panel, "Formulae", "formula")
        self.casks_list = self._build_list_panel(left_panel, "Casks", "cask")
        content.add(left_panel, weight=3)

        details_panel = ttk.Frame(content, padding=8)
        details_panel.columnconfigure(0, weight=1)
        details_panel.rowconfigure(3, weight=1)
        details_panel.rowconfigure(5, weight=1)
        ttk.Label(details_panel, text="Selection", font=("Helvetica", 14, "bold")).grid(
            row=0,
            column=0,
            sticky="w",
            pady=(0, 8),
        )
        ttk.Label(details_panel, textvariable=self.selection_var).grid(
            row=1,
            column=0,
            sticky="w",
        )
        buttons = ttk.Frame(details_panel)
        buttons.grid(row=2, column=0, sticky="w", pady=(8, 8))
        ttk.Button(buttons, text="Show Details", command=self._show_selected_details).grid(row=0, column=0)
        ttk.Button(buttons, text="Upgrade Selected", command=self._upgrade_selected).grid(
            row=0,
            column=1,
            padx=(8, 0),
        )
        ttk.Button(buttons, text="Uninstall Selected", command=self._uninstall_selected).grid(
            row=0,
            column=2,
            padx=(8, 0),
        )

        self.details_text = tk.Text(details_panel, wrap="word", height=14)
        self.details_text.grid(row=3, column=0, sticky="nsew")

        ttk.Label(details_panel, text="Command Log", font=("Helvetica", 14, "bold")).grid(
            row=4,
            column=0,
            sticky="w",
            pady=(12, 8),
        )
        self.log_text = tk.Text(details_panel, wrap="word", height=10)
        self.log_text.grid(row=5, column=0, sticky="nsew")
        content.add(details_panel, weight=2)

    def _build_list_panel(
        self,
        parent: ttk.Panedwindow,
        title: str,
        package_kind: str,
    ) -> tk.Listbox:
        frame = ttk.Frame(parent, padding=8)
        frame.columnconfigure(0, weight=1)
        frame.rowconfigure(1, weight=1)

        ttk.Label(frame, text=title, font=("Helvetica", 14, "bold")).grid(
            row=0,
            column=0,
            sticky="w",
            pady=(0, 8),
        )

        listbox = tk.Listbox(frame, activestyle="none")
        scrollbar = ttk.Scrollbar(frame, orient=tk.VERTICAL, command=listbox.yview)
        listbox.configure(yscrollcommand=scrollbar.set)
        listbox.bind("<<ListboxSelect>>", lambda _event: self._handle_selection(listbox, package_kind))
        listbox.grid(row=1, column=0, sticky="nsew")
        scrollbar.grid(row=1, column=1, sticky="ns")
        parent.add(frame, weight=1)
        return listbox

    def refresh(self) -> None:
        snapshot = self.service.collect_snapshot()
        self._render_snapshot(snapshot)

    def _render_snapshot(self, snapshot: BrewSnapshot) -> None:
        if snapshot.available:
            self.status_var.set(
                f"{snapshot.version} | Formulae: {len(snapshot.formulae)} | Casks: {len(snapshot.casks)}"
            )
        else:
            self.status_var.set("Homebrew unavailable")

        self.error_var.set(snapshot.error)
        self._all_formulae = snapshot.formulae
        self._all_casks = snapshot.casks
        self.summary_var.set(
            f"Outdated formulae: {len(snapshot.outdated_formulae)} | Outdated casks: {len(snapshot.outdated_casks)}"
        )
        self._apply_filter()

    def _apply_filter(self) -> None:
        keyword = self.filter_var.get().strip().lower()
        formulae = self._filter_items(getattr(self, "_all_formulae", []), keyword)
        casks = self._filter_items(getattr(self, "_all_casks", []), keyword)
        self._replace_listbox(self.formulae_list, formulae)
        self._replace_listbox(self.casks_list, casks)

    @staticmethod
    def _filter_items(items: list[str], keyword: str) -> list[str]:
        if not keyword:
            return items
        return [item for item in items if keyword in item.lower()]

    @staticmethod
    def _replace_listbox(listbox: tk.Listbox, items: list[str]) -> None:
        listbox.delete(0, tk.END)
        for item in items:
            listbox.insert(tk.END, item)

    def _handle_selection(self, listbox: tk.Listbox, package_kind: str) -> None:
        selection = listbox.curselection()
        if not selection:
            return
        name = listbox.get(selection[0])
        self._selected_package = PackageSelection(name=name, kind=package_kind)
        self.selection_var.set(f"{name} ({package_kind})")

    def _show_selected_details(self) -> None:
        if self._selected_package is None:
            self._append_log("No package selected for details.")
            return

        try:
            details = self.service.get_package_details(
                self._selected_package.name,
                self._selected_package.kind,
            )
        except Exception as exc:  # noqa: BLE001
            self.error_var.set(str(exc))
            self._append_log(f"Failed to fetch details: {exc}")
            return

        self._set_text(self.details_text, details)
        self._append_log(
            f"Loaded details for {self._selected_package.name} ({self._selected_package.kind})."
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
        result = self.service.run_action(
            action,
            package_name=package_name,
            package_kind=package_kind,
        )
        self._handle_command_result(result)
        if result.succeeded:
            self.refresh()

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
