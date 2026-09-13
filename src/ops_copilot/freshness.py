"""Freshness SLA check: PASS/FAIL plus age_hours."""

from __future__ import annotations

from ops_copilot.types import Chunk, FreshnessResult, FreshnessStatus


def age_passes(age_hours: float, max_age_hours: float) -> bool:
    """Inclusive SLA: a document at exactly max_age_hours still passes."""
    if max_age_hours < 0:
        raise ValueError("max_age_hours must be >= 0")
    return age_hours <= max_age_hours


def check_freshness(chunk: Chunk, max_age_hours: float) -> FreshnessResult:
    status = FreshnessStatus.PASS if age_passes(chunk.age_hours, max_age_hours) else FreshnessStatus.FAIL
    return FreshnessResult(
        status=status,
        age_hours=chunk.age_hours,
        max_age_hours=max_age_hours,
        doc_id=chunk.doc_id,
        chunk_id=chunk.chunk_id,
    )


def annotate(chunks: list[Chunk], max_age_hours: float) -> list[FreshnessResult]:
    return [check_freshness(chunk, max_age_hours) for chunk in chunks]


def fresh_only(chunks: list[Chunk], max_age_hours: float) -> list[Chunk]:
    return [c for c in chunks if age_passes(c.age_hours, max_age_hours)]
