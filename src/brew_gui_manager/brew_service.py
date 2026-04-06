from __future__ import annotations

from dataclasses import dataclass
import json
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


@dataclass(slots=True)
class PackageDetails:
    name: str
    kind: PackageKind
    title: str
    description: str
    homepage: str
    latest_version: str
    installed_versions: list[str]
    dependencies: list[str]
    tap: str
    caveats: str
    raw_text: str


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

    def get_package_details(self, package_name: str, package_kind: PackageKind) -> PackageDetails:
        try:
            payload = self._run(self.executable, "info", "--json=v2", package_name)
            return self._parse_package_details_json(package_name, package_kind, payload)
        except (subprocess.CalledProcessError, json.JSONDecodeError, KeyError, IndexError, TypeError, ValueError):
            raw_text = self._run(self.executable, "info", self._kind_flag(package_kind), package_name)
            return PackageDetails(
                name=package_name,
                kind=package_kind,
                title=package_name,
                description="Structured metadata unavailable. Showing raw Homebrew info.",
                homepage="",
                latest_version="Unknown",
                installed_versions=[],
                dependencies=[],
                tap="",
                caveats="",
                raw_text=raw_text,
            )

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

    def _parse_package_details_json(
        self,
        package_name: str,
        package_kind: PackageKind,
        payload: str,
    ) -> PackageDetails:
        data = json.loads(payload)
        key = "casks" if package_kind == "cask" else "formulae"
        entries = data.get(key, [])
        package = next(
            (
                item
                for item in entries
                if item.get("name") == package_name or item.get("token") == package_name
            ),
            None,
        )
        if package is None:
            if not entries:
                raise ValueError(f"No package details returned for {package_name}")
            package = entries[0]

        if package_kind == "cask":
            installed_versions = self._parse_cask_versions(package)
            latest_version = str(package.get("version") or "Unknown")
            title = package.get("name") or package.get("token") or package_name
            homepage = str(package.get("homepage") or "")
            description = str(package.get("desc") or "No description available.")
            dependencies = [str(item) for item in package.get("depends_on", {}).get("formula", [])]
            tap = str(package.get("tap") or "")
            caveats = str(package.get("caveats") or "")
        else:
            installed_versions = [
                str(item.get("version"))
                for item in package.get("installed", [])
                if item.get("version")
            ]
            latest_version = str(package.get("versions", {}).get("stable") or "Unknown")
            title = package.get("name") or package_name
            homepage = str(package.get("homepage") or "")
            description = str(package.get("desc") or "No description available.")
            dependencies = [str(item) for item in package.get("dependencies", [])]
            tap = str(package.get("tap") or "")
            caveats = str(package.get("caveats") or "")

        raw_text = self._run(self.executable, "info", self._kind_flag(package_kind), package_name)
        return PackageDetails(
            name=package_name,
            kind=package_kind,
            title=title,
            description=description,
            homepage=homepage,
            latest_version=latest_version,
            installed_versions=installed_versions,
            dependencies=dependencies,
            tap=tap,
            caveats=caveats,
            raw_text=raw_text,
        )

    @staticmethod
    def _parse_cask_versions(package: dict) -> list[str]:
        installed_items = package.get("installed") or []
        versions: list[str] = []
        for item in installed_items:
            if isinstance(item, str):
                versions.append(item)
            elif isinstance(item, dict) and item.get("version"):
                versions.append(str(item["version"]))
        return versions

    def _run(self, *args: str) -> str:
        completed = subprocess.run(
            args,
            check=True,
            capture_output=True,
            text=True,
        )
        return completed.stdout.strip()
