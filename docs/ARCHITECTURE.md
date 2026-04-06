# Architecture

## Layers

### UI Layer

- File: `src/brew_gui_manager/app.py`
- Owns Tk layout, selection state, and presentation-only formatting.
- Must not call `subprocess` directly.

### Service Layer

- File: `src/brew_gui_manager/brew_service.py`
- Owns Homebrew command construction, CLI invocation, and parsing.
- Returns structured dataclasses instead of raw UI-specific strings when possible.

### Runtime Layer

- File: `src/brew_gui_manager/task_runner.py`
- Owns background execution and message passing between worker threads and Tk.
- UI should communicate through this layer for long-running work.

## Invariants

- Every Homebrew command should be observable in the UI log.
- UI startup should paint before any expensive Homebrew work begins.
- Package selection should remain valid even when category filters change.
- Failures should preserve stderr where available.

## Testing Strategy

- Service and runtime layers get unit tests.
- UI gets smoke tests that instantiate the app and pump one Tk update cycle.
- Favor standard library tooling where it keeps bootstrap friction low.
