from __future__ import annotations

from dataclasses import dataclass


PackageKind = str


@dataclass(slots=True)
class PackageSelection:
    name: str
    kind: PackageKind
