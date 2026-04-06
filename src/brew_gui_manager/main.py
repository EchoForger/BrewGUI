from __future__ import annotations

import tkinter as tk

from .app import BrewManagerApp


def main() -> None:
    root = tk.Tk()
    BrewManagerApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()

