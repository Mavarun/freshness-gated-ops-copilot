"""Load and resolve per-source freshness SLAs.

A single global ``max_age_hours`` either over-refuses durable wiki/policy pages
or under-protects live scrape sources. This module maps ``source_system`` →
``max_age_hours`` with a configurable global fallback.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Mapping

import yaml

DEFAULT_SLA_PATH = (
    Path(__file__).resolve().parents[2] / "config" / "source_slas.yaml"
)


@dataclass(frozen=True)
class SourceSlaTable:
    """Immutable lookup of per-source max ages plus the global fallback."""

    global_default_hours: float
    sources: Mapping[str, float]
    path: str | None = None

    def max_age_hours(self, source_system: str) -> float:
        key = (source_system or "").strip().lower()
        if key in self.sources:
            return float(self.sources[key])
        return float(self.global_default_hours)

    def as_dict(self) -> dict:
        return {
            "global_default_hours": self.global_default_hours,
            "sources": dict(self.sources),
            "path": self.path,
        }


def load_source_slas(path: str | Path | None = None) -> SourceSlaTable:
    """Parse ``config/source_slas.yaml`` (or an override path)."""
    src = Path(path) if path else DEFAULT_SLA_PATH
    if not src.is_file():
        raise FileNotFoundError(f"source SLA config not found: {src}")
    with src.open(encoding="utf-8") as handle:
        raw = yaml.safe_load(handle) or {}
    if not isinstance(raw, dict):
        raise ValueError(f"{src}: expected a mapping at the top level")

    global_default = float(raw.get("global_default_hours", 48.0))
    if global_default < 0:
        raise ValueError(f"{src}: global_default_hours must be >= 0")

    sources_raw = raw.get("sources") or {}
    if not isinstance(sources_raw, dict):
        raise ValueError(f"{src}: sources must be a mapping")

    sources: dict[str, float] = {}
    for name, hours in sources_raw.items():
        key = str(name).strip().lower()
        if not key:
            raise ValueError(f"{src}: empty source_system key")
        value = float(hours)
        if value < 0:
            raise ValueError(f"{src}: SLA for {key!r} must be >= 0")
        sources[key] = value

    return SourceSlaTable(
        global_default_hours=global_default,
        sources=sources,
        path=str(src),
    )


def resolve_max_age(
    source_system: str,
    *,
    table: SourceSlaTable | None = None,
    global_default_hours: float = 48.0,
    use_source_slas: bool = True,
) -> float:
    """Return the SLA that applies to ``source_system``.

    When ``use_source_slas`` is False, always return ``global_default_hours``
    (the v0 global-only behaviour). When True and a table is provided, look up
    the source and fall back to the table's global default (or the explicit
    ``global_default_hours`` if the table is absent).
    """
    if not use_source_slas:
        return float(global_default_hours)
    if table is None:
        return float(global_default_hours)
    return table.max_age_hours(source_system)
