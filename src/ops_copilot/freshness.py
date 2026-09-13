"""Freshness SLA check: PASS/FAIL plus age_hours.

Supports a single global max_age_hours (v0) or a per-source lookup that
falls back to the global default for unknown source_system values.
"""

from __future__ import annotations

from collections.abc import Callable

from ops_copilot.types import Chunk, FreshnessResult, FreshnessStatus

SlaLookup = Callable[[str], float]


def age_passes(age_hours: float, max_age_hours: float) -> bool:
    """Inclusive SLA: a document at exactly max_age_hours still passes."""
    if max_age_hours < 0:
        raise ValueError("max_age_hours must be >= 0")
    return age_hours <= max_age_hours


def _resolve_sla(
    chunk: Chunk,
    max_age_hours: float | None,
    sla_lookup: SlaLookup | None,
) -> float:
    if sla_lookup is not None:
        return float(sla_lookup(chunk.source_system))
    if max_age_hours is None:
        raise ValueError("max_age_hours or sla_lookup is required")
    return float(max_age_hours)


def check_freshness(
    chunk: Chunk,
    max_age_hours: float | None = None,
    *,
    sla_lookup: SlaLookup | None = None,
) -> FreshnessResult:
    applied = _resolve_sla(chunk, max_age_hours, sla_lookup)
    status = FreshnessStatus.PASS if age_passes(chunk.age_hours, applied) else FreshnessStatus.FAIL
    return FreshnessResult(
        status=status,
        age_hours=chunk.age_hours,
        max_age_hours=applied,
        doc_id=chunk.doc_id,
        chunk_id=chunk.chunk_id,
        source_system=chunk.source_system,
    )


def annotate(
    chunks: list[Chunk],
    max_age_hours: float | None = None,
    *,
    sla_lookup: SlaLookup | None = None,
) -> list[FreshnessResult]:
    return [check_freshness(c, max_age_hours, sla_lookup=sla_lookup) for c in chunks]


def fresh_only(
    chunks: list[Chunk],
    max_age_hours: float | None = None,
    *,
    sla_lookup: SlaLookup | None = None,
) -> list[Chunk]:
    kept: list[Chunk] = []
    for chunk in chunks:
        applied = _resolve_sla(chunk, max_age_hours, sla_lookup)
        if age_passes(chunk.age_hours, applied):
            kept.append(chunk)
    return kept
