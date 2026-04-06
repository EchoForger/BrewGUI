from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from .brew_service import BrewService, BrewSnapshot


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
        ttk.Button(header, text="Refresh", command=self.refresh).grid(
            row=0,
            column=1,
            sticky="e",
        )

        status_panel = ttk.Frame(container, padding=(0, 12, 0, 12))
        status_panel.grid(row=1, column=0, sticky="ew")
        status_panel.columnconfigure(1, weight=1)

        ttk.Label(status_panel, text="Status:").grid(row=0, column=0, sticky="w")
        ttk.Label(status_panel, textvariable=self.status_var).grid(
            row=0,
            column=1,
            sticky="w",
        )
        ttk.Label(status_panel, text="Filter:").grid(row=1, column=0, sticky="w")
        ttk.Entry(status_panel, textvariable=self.filter_var).grid(
            row=1,
            column=1,
            sticky="ew",
            pady=(8, 0),
        )
        ttk.Label(
            status_panel,
            textvariable=self.error_var,
            foreground="#9a3412",
        ).grid(row=2, column=0, columnspan=2, sticky="w", pady=(8, 0))

        content = ttk.Panedwindow(container, orient=tk.HORIZONTAL)
        content.grid(row=2, column=0, sticky="nsew")

        self.formulae_list = self._build_list_panel(content, "Formulae")
        self.casks_list = self._build_list_panel(content, "Casks")

    def _build_list_panel(self, parent: ttk.Panedwindow, title: str) -> tk.Listbox:
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

