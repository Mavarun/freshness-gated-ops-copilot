"""Tiny FastAPI surface for the freshness-gated ops copilot demo.

Exposes decision, reasons, evidence ages, and trace_id — not just answer text.
Offline; no paid LLM. Traces append to artifacts/traces.jsonl as elsewhere.
"""

from __future__ import annotations

import uuid
from functools import lru_cache
from typing import Any

from fastapi import FastAPI, HTTPException

from ops_copilot import Copilot, CopilotConfig, __version__
from ops_copilot.api_schemas import EvidenceItem, QueryRequest, QueryResponse
from ops_copilot.config import parse_clock
from ops_copilot.trace import TraceWriter
from ops_copilot.types import CopilotResult, FreshnessResult

app = FastAPI(
    title="Freshness-gated ops copilot",
    description=(
        "Demo HTTP surface: POST /query returns ANSWER | REFUSE_* with evidence "
        "ages and trace_id. Offline extractive path; no paid LLM."
    ),
    version=__version__,
)

_tracer = TraceWriter()


@lru_cache(maxsize=8)
def _copilot_for_clock(clock_key: str) -> Copilot:
    """Cache Copilot instances keyed by normalized clock ISO string."""
    now = parse_clock(None if clock_key == "" else clock_key)
    return Copilot(config=CopilotConfig(), now=now)


def get_copilot(clock: str | None = None) -> Copilot:
    key = "" if clock is None else parse_clock(clock).isoformat()
    return _copilot_for_clock(key)


def _freshness_by_chunk(result: CopilotResult) -> dict[str, FreshnessResult]:
    return {f.chunk_id: f for f in result.freshness}


def _sla_used(copilot: Copilot, result: CopilotResult) -> dict[str, Any]:
    """Summarize which SLAs applied to retrieved evidence."""
    cfg = copilot.config
    per_source: dict[str, float] = {}
    for chunk in result.retrieved:
        src = chunk.source_system
        if src not in per_source:
            per_source[src] = copilot.sla_for(src)
    table = copilot.sla_table.as_dict() if copilot.sla_table is not None else None
    return {
        "mode": "per_source" if cfg.use_source_slas else "global",
        "global_default_hours": cfg.max_age_hours,
        "per_source": per_source,
        "table": table,
    }


def result_to_response(
    result: CopilotResult, *, trace_id: str, sla_used: dict[str, Any]
) -> QueryResponse:
    freshes = _freshness_by_chunk(result)
    evidence: list[EvidenceItem] = []
    for chunk in result.retrieved:
        fr = freshes.get(chunk.chunk_id)
        evidence.append(
            EvidenceItem(
                chunk_id=chunk.chunk_id,
                doc_id=chunk.doc_id,
                title=chunk.title,
                source_system=chunk.source_system,
                updated_at=chunk.updated_at.isoformat(),
                age_hours=round(chunk.age_hours, 4),
                score=round(chunk.score, 4),
                freshness_status=fr.status.value if fr else None,
                max_age_hours=fr.max_age_hours if fr else None,
            )
        )
    return QueryResponse(
        decision=result.decision.value,
        answer_or_refusal=result.answer,
        reason=result.reason,
        evidence=evidence,
        ages=[round(c.age_hours, 4) for c in result.retrieved],
        sla_used=sla_used,
        latency_ms=round(result.latency_ms, 3),
        trace_id=trace_id,
        cited_ids=list(result.cited_ids),
        grounding=result.grounding.as_dict() if result.grounding else None,
    )


@app.post("/query", response_model=QueryResponse)
def query(body: QueryRequest) -> QueryResponse:
    """Run retrieve → support → freshness → extract → policy; write a JSONL trace."""
    q = body.query.strip()
    if not q:
        raise HTTPException(status_code=422, detail="query must not be empty")
    try:
        copilot = get_copilot(body.clock)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=f"invalid clock: {exc}") from exc

    result = copilot.ask(q)
    trace_id = str(uuid.uuid4())
    sla = _sla_used(copilot, result)
    _tracer.write(result, extra={"trace_id": trace_id, "sla_used": sla})
    return result_to_response(result, trace_id=trace_id, sla_used=sla)


def create_app() -> FastAPI:
    """Factory for tests and ASGI servers."""
    return app
