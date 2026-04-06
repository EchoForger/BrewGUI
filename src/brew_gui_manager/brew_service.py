from __future__ import annotations

from dataclasses import dataclass
import shutil
import subprocess


@dataclass(slots=True)
class BrewSnapshot:
    available: bool
    version: str
    formulae: list[str]
    casks: list[str]
    error: str = ""


class BrewService:
    """Small wrapper around the Homebrew CLI."""

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
                error="Homebrew executable was not found in PATH.",
            )

        try:
            version = self._run(self.executable, "--version").splitlines()[0]
            formulae = self._run(self.executable, "list", "--formula").splitlines()
            casks = self._run(self.executable, "list", "--cask").splitlines()
        except subprocess.CalledProcessError as exc:
            return BrewSnapshot(
                available=True,
                version="Unknown",
                formulae=[],
                casks=[],
                error=exc.stderr.strip() or str(exc),
            )

        return BrewSnapshot(
            available=True,
            version=version,
            formulae=[item for item in formulae if item],
            casks=[item for item in casks if item],
        )

    def _run(self, *args: str) -> str:
        completed = subprocess.run(
            args,
            check=True,
            capture_output=True,
            text=True,
        )
        return completed.stdout.strip()
