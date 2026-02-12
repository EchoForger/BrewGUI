import argparse
import sys
from .app import run_app
from . import __version__


def main(argv=None):
    argv = argv if argv is not None else sys.argv[1:]
    p = argparse.ArgumentParser(prog="brewgui", description="BrewGUI - Homebrew GUI (Tkinter)")
    p.add_argument("--version", action="store_true", help="Show version and exit")
    args = p.parse_args(argv)

    if args.version:
        print(__version__)
        return 0

    run_app()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
