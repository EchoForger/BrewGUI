# Async Storefront Execution Plan

## Goal

Move Homebrew work off the Tk main thread and improve the selected package page with richer, structured metadata.

## Why

- Startup still depends on Homebrew latency
- Install and upgrade flows can freeze the interface
- The detail pane looks like a log dump instead of an app page

## Scope

- Add a background task runner for refresh, details, install, upgrade, uninstall, and cleanup
- Surface visible busy state and action disabling in the UI
- Parse `brew info --json=v2` when available to produce structured package details

## Acceptance Criteria

- Refresh and package actions do not block the window from repainting
- Users can see when work is running
- The app page shows structured metadata for a selected package
- Service and runtime tests cover the new paths
