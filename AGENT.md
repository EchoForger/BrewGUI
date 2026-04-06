# AGENT Guide

This file is the table of contents for repository knowledge. Keep it short and stable.

## What This Product Is

`brew-gui` is a macOS desktop storefront for Homebrew. It should feel approachable like an app marketplace while still exposing reliable package-management controls.

## Core Rules

- Keep subprocess interaction inside [`src/brew_gui_manager/brew_service.py`](/Users/wuhaonan/Downloads/test/src/brew_gui_manager/brew_service.py).
- Keep Tk widget orchestration inside [`src/brew_gui_manager/app.py`](/Users/wuhaonan/Downloads/test/src/brew_gui_manager/app.py).
- Long-running Homebrew work must not block the Tk main thread.
- Dangerous actions require confirmation and must leave visible logs.
- Prefer repo-local documentation over chat-only decisions.

## Where To Look Next

- Product intent: [`docs/product-specs/storefront.md`](/Users/wuhaonan/Downloads/test/docs/product-specs/storefront.md)
- Architecture boundaries: [`docs/ARCHITECTURE.md`](/Users/wuhaonan/Downloads/test/docs/ARCHITECTURE.md)
- Active execution plans: [`docs/PLANS.md`](/Users/wuhaonan/Downloads/test/docs/PLANS.md)
- Milestones: [`docs/roadmap.md`](/Users/wuhaonan/Downloads/test/docs/roadmap.md)

## Current Priorities

- Make all brew operations background-safe
- Increase detail richness for selected packages
- Keep the storefront responsive during installs, upgrades, and refreshes
