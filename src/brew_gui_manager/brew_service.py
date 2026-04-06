from __future__ import annotations

from dataclasses import dataclass
import shutil
import subprocess
from typing import Final


PackageKind = str


@dataclass(slots=True)
class BrewSnapshot:
    available: bool
    version: str
    formulae: list[str]
    casks: list[str]
    outdated_formulae: list[str]
    outdated_casks: list[str]
    error: str = ""


@dataclass(slots=True)
class BrewCommandResult:
    command: tuple[str, ...]
    succeeded: bool
    output: str = ""
    error: str = ""


class BrewService:
    """Small wrapper around the Homebrew CLI."""

    ACTIONS: Final[dict[str, tuple[str, ...]]] = {
        "upgrade_all": ("upgrade",),
        "cleanup": ("cleanup",),
    }

    def __init__(self, executable: str = "brew") -> None:
        self.executable = executable

    def is_available(self) -> bool:
        return shutil.which(self.executable) is not None

    def collect_snapshot(self) -> BrewSnapshot:
        if not self.is_available():
            return BrewSnapshot(
                available=False,
                version="Not installed",
                formulae=[],
                casks=[],
                outdated_formulae=[],
                outdated_casks=[],
                error="Homebrew executable was not found in PATH.",
            )

        try:
            version = self._run(self.executable, "--version").splitlines()[0]
            formulae = self._run(self.executable, "list", "--formula").splitlines()
            casks = self._run(self.executable, "list", "--cask").splitlines()
            outdated_formulae = self._run(
                self.executable,
                "outdated",
                "--quiet",
                "--formula",
            ).splitlines()
            outdated_casks = self._run(
                self.executable,
                "outdated",
                "--quiet",
                "--cask",
            ).splitlines()
        except subprocess.CalledProcessError as exc:
            return BrewSnapshot(
                available=True,
                version="Unknown",
                formulae=[],
                casks=[],
                outdated_formulae=[],
                outdated_casks=[],
                error=exc.stderr.strip() or str(exc),
            )

        return BrewSnapshot(
            available=True,
            version=version,
            formulae=[item for item in formulae if item],
            casks=[item for item in casks if item],
            outdated_formulae=[item for item in outdated_formulae if item],
            outdated_casks=[item for item in outdated_casks if item],
        )

    def get_package_details(self, package_name: str, package_kind: PackageKind) -> str:
        return self._run(self.executable, "info", self._kind_flag(package_kind), package_name)

    def run_action(
        self,
        action: str,
        package_name: str = "",
        package_kind: PackageKind = "formula",
    ) -> BrewCommandResult:
        command = self._build_action_command(action, package_name, package_kind)
        if command is None:
            return BrewCommandResult(
                command=(),
                succeeded=False,
                error=f"Unknown action: {action}",
            )

        if package_name == "" and action in {"install_formula", "install_cask", "uninstall_formula", "uninstall_cask"}:
            return BrewCommandResult(
                command=command,
                succeeded=False,
                error=f"Action '{action}' requires a package name.",
            )

        try:
            output = self._run(*command)
        except subprocess.CalledProcessError as exc:
            return BrewCommandResult(
                command=command,
                succeeded=False,
                output=(exc.stdout or "").strip(),
                error=(exc.stderr or "").strip() or str(exc),
            )

        return BrewCommandResult(
            command=command,
            succeeded=True,
            output=output,
        )

    def _build_action_command(
        self,
        action: str,
        package_name: str,
        package_kind: PackageKind,
    ) -> tuple[str, ...] | None:
        if action in self.ACTIONS:
            return (self.executable, *self.ACTIONS[action])

        if action == "install_formula":
            return (self.executable, "install", package_name)
        if action == "install_cask":
            return (self.executable, "install", "--cask", package_name)
        if action == "uninstall_formula":
            return (self.executable, "uninstall", package_name)
        if action == "uninstall_cask":
            return (self.executable, "uninstall", "--cask", package_name)
        if action == "upgrade_selected":
            return (
                self.executable,
                "upgrade",
                *(("--cask",) if package_kind == "cask" else ()),
                package_name,
            )
        return None

    @staticmethod
    def _kind_flag(package_kind: PackageKind) -> str:
        return "--cask" if package_kind == "cask" else "--formula"

    def _run(self, *args: str) -> str:
        completed = subprocess.run(
            args,
            check=True,
            capture_output=True,
            text=True,
        )
        return completed.stdout.strip()
