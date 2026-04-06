from __future__ import annotations

import unittest
from subprocess import CalledProcessError
from unittest.mock import patch

from brew_gui_manager.brew_service import BrewCommandResult, BrewService


class BrewServiceTests(unittest.TestCase):
    def test_collect_snapshot_without_brew(self) -> None:
        service = BrewService()

        with patch.object(service, "is_available", return_value=False):
            snapshot = service.collect_snapshot()

        self.assertFalse(snapshot.available)
        self.assertEqual(snapshot.formulae, [])
        self.assertIn("not found", snapshot.error.lower())

    def test_collect_snapshot_success(self) -> None:
        service = BrewService()
        results = {
            ("brew", "--version"): "Homebrew 4.3.0",
            ("brew", "list", "--formula"): "wget\npython@3.12",
            ("brew", "list", "--cask"): "iterm2\nraycast",
            ("brew", "outdated", "--quiet", "--formula"): "git",
            ("brew", "outdated", "--quiet", "--cask"): "wezterm",
        }

        with patch.object(service, "is_available", return_value=True):
            with patch.object(service, "_run", side_effect=lambda *args: results[args]):
                snapshot = service.collect_snapshot()

        self.assertTrue(snapshot.available)
        self.assertEqual(snapshot.version, "Homebrew 4.3.0")
        self.assertEqual(snapshot.formulae, ["wget", "python@3.12"])
        self.assertEqual(snapshot.casks, ["iterm2", "raycast"])
        self.assertEqual(snapshot.outdated_formulae, ["git"])
        self.assertEqual(snapshot.outdated_casks, ["wezterm"])

    def test_collect_snapshot_handles_subprocess_failure(self) -> None:
        service = BrewService()

        def boom(*_args: str) -> str:
            raise CalledProcessError(1, ["brew"], stderr="mocked failure")

        with patch.object(service, "is_available", return_value=True):
            with patch.object(service, "_run", side_effect=boom):
                snapshot = service.collect_snapshot()

        self.assertTrue(snapshot.available)
        self.assertEqual(snapshot.error, "mocked failure")

    def test_get_package_details_for_formula(self) -> None:
        service = BrewService()

        with patch.object(service, "_run", return_value="formula details") as run_mock:
            details = service.get_package_details("wget", "formula")

        self.assertEqual(details, "formula details")
        run_mock.assert_called_once_with("brew", "info", "--formula", "wget")

    def test_run_action_success(self) -> None:
        service = BrewService()

        with patch.object(service, "_run", return_value="done") as run_mock:
            result = service.run_action("upgrade_all")

        self.assertEqual(
            result,
            BrewCommandResult(
                command=("brew", "upgrade"),
                succeeded=True,
                output="done",
                error="",
            ),
        )
        run_mock.assert_called_once_with("brew", "upgrade")

    def test_run_action_requires_package_name(self) -> None:
        service = BrewService()

        result = service.run_action("uninstall_formula")

        self.assertFalse(result.succeeded)
        self.assertIn("requires a package name", result.error)

    def test_run_action_handles_failure(self) -> None:
        service = BrewService()

        def boom(*_args: str) -> str:
            raise CalledProcessError(1, ["brew", "cleanup"], stderr="cleanup failed")

        with patch.object(service, "_run", side_effect=boom):
            result = service.run_action("cleanup")

        self.assertFalse(result.succeeded)
        self.assertEqual(result.error, "cleanup failed")


if __name__ == "__main__":
    unittest.main()
