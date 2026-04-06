from __future__ import annotations

from subprocess import CalledProcessError

from brew_gui_manager.brew_service import BrewService


def test_collect_snapshot_without_brew(monkeypatch) -> None:
    service = BrewService()
    monkeypatch.setattr(service, "is_available", lambda: False)

    snapshot = service.collect_snapshot()

    assert snapshot.available is False
    assert snapshot.formulae == []
    assert "not found" in snapshot.error.lower()


def test_collect_snapshot_success(monkeypatch) -> None:
    service = BrewService()
    monkeypatch.setattr(service, "is_available", lambda: True)

    results = {
        ("brew", "--version"): "Homebrew 4.3.0",
        ("brew", "list", "--formula"): "wget\npython@3.12",
        ("brew", "list", "--cask"): "iterm2\nraycast",
    }

    monkeypatch.setattr(service, "_run", lambda *args: results[args])

    snapshot = service.collect_snapshot()

    assert snapshot.available is True
    assert snapshot.version == "Homebrew 4.3.0"
    assert snapshot.formulae == ["wget", "python@3.12"]
    assert snapshot.casks == ["iterm2", "raycast"]


def test_collect_snapshot_handles_subprocess_failure(monkeypatch) -> None:
    service = BrewService()
    monkeypatch.setattr(service, "is_available", lambda: True)

    def _boom(*_args: str) -> str:
        raise CalledProcessError(1, ["brew"], stderr="mocked failure")

    monkeypatch.setattr(service, "_run", _boom)

    snapshot = service.collect_snapshot()

    assert snapshot.available is True
    assert snapshot.error == "mocked failure"
