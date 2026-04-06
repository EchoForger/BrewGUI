# Agent Notes

## Product Direction

Build a desktop GUI for Homebrew that makes package management approachable and visible.

## Initial Scope

- Show Homebrew availability and version
- List installed formulae and casks
- Refresh package lists from the GUI
- Reserve clear extension points for install, upgrade, uninstall, and diagnostics

## Architecture Guidelines

- Keep UI code in `app.py`
- Keep shell interaction isolated in `brew_service.py`
- Avoid mixing subprocess calls directly into widget callbacks
- Prefer small, testable methods over large event handlers

## Collaboration Notes

- Treat Homebrew command execution as an integration boundary
- Mock `subprocess.run` in tests
- Keep the first version dependency-light to simplify bootstrap on macOS

