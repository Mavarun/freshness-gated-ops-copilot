"""Pydantic request/response models for the demo HTTP surface."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class QueryRequest(BaseModel):
    """POST /query body. ``clock`` overrides the frozen EVAL_CLOCK for demos."""

    query: str = Field(..., min_length=1, description="Ops question to ask the copilot")
    clock: str | None = Field(
        default=None,
        description="Optional ISO-8601 clock override (else EVAL_CLOCK / OPS_COPILOT_NOW)",
    )
    session_id: str | None = Field(
        default=None,
        description="Optional session id for cost-budget accumulation (also accepted via X-Session-Id header)",
    )


class EvidenceItem(BaseModel):
    """One retrieved chunk exposed in the HTTP response."""

    chunk_id: str
    doc_id: str
    title: str
    source_system: str
    updated_at: str
    age_hours: float
    score: float
    freshness_status: str | None = None
    max_age_hours: float | None = None


class QueryResponse(BaseModel):
    """Structured decision surface — not just answer text."""

    decision: str
    answer_or_refusal: str
    reason: str
    evidence: list[EvidenceItem]
    ages: list[float]
    sla_used: dict[str, Any]
    latency_ms: float
    trace_id: str
    cited_ids: list[str] = Field(default_factory=list)
    grounding: dict[str, Any] | None = None
    disagreement: dict[str, Any] | None = None
    approx_cost_units: float | None = None
    session_id: str | None = None
    session_spent_before: float | None = None
    session_spent_after: float | None = None
    session_budget: float | None = None


class HealthResponse(BaseModel):
    status: str
    clock: str
    version: str
    use_source_slas: bool
    corpus_docs: int
    corpus_chunks: int


class SourcesResponse(BaseModel):
    """Per-source freshness SLA table (+ global fallback)."""

    global_default_hours: float
    sources: dict[str, float]
    path: str | None = None
    use_source_slas: bool = True
