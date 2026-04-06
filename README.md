# Brew GUI Manager

`Brew GUI Manager` is a Python desktop application for managing Homebrew from a graphical interface.

## Goals

- View Homebrew environment status
- Search installed formulae and casks
- Trigger common actions such as refresh, install, upgrade, and cleanup
- Keep the architecture simple enough for rapid iteration

## Tech Choices

- Python 3.10+
- `tkinter` for the initial desktop UI
- `subprocess` to call the `brew` CLI

## Quick Start

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
python -m brew_gui_manager
```

Or run:

```bash
brew-gui
```

## Project Structure

```text
.
├── AGENT.md
├── README.md
├── docs/
│   ├── ARCHITECTURE.md
│   ├── PLANS.md
│   ├── exec-plans/
│   ├── product-specs/
│   └── roadmap.md
├── pyproject.toml
├── src/
│   └── brew_gui_manager/
│       ├── __init__.py
│       ├── app.py
│       ├── brew_service.py
│       └── main.py
└── tests/
    └── test_brew_service.py
```

## Next Suggestions

- Parse `brew info --json=v2` for richer metadata
- Introduce background tasks for long-running operations
- Package the app for macOS distribution

## Current Features

- Refresh and inspect installed formulae and casks
- Filter package lists in real time
- Install a formula or cask from the main window
- Upgrade all packages or just the selected package
- Uninstall the selected formula or cask with confirmation
- View package details from `brew info`
- Inspect a simple in-app command log

## Repository Guidance

- [`AGENT.md`](/Users/wuhaonan/Downloads/test/AGENT.md) is the short entry point for agents
- Product and architecture decisions live under [`docs/`](/Users/wuhaonan/Downloads/test/docs)
