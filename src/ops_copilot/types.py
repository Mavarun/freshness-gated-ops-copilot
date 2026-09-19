"""Shared dataclasses and decision enums."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class Decision(str, Enum):
    ANSWER = "ANSWER"
    REFUSE_STALE = "REFUSE_STALE"
    REFUSE_UNGROUNDED = "REFUSE_UNGROUNDED"
    REFUSE_NO_EVIDENCE = "REFUSE_NO_EVIDENCE"
    REFUSE_DISAGREE = "REFUSE_DISAGREE"
    REFUSE_CANARY = "REFUSE_CANARY"


class FreshnessStatus(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"


@dataclass
class Document:
    doc_id: str
    title: str
    body: str
    updated_at: datetime
    source_system: str


@dataclass
class Chunk:
    chunk_id: str
    doc_id: str
    title: str
    text: str
    updated_at: datetime
    source_system: str
    age_hours: float
    score: float = 0.0
    bm25: float = 0.0
    dense: float = 0.0

    def as_dict(self) -> dict:
        return {
            "chunk_id": self.chunk_id,
            "doc_id": self.doc_id,
            "title": self.title,
            "source_system": self.source_system,
            "updated_at": self.updated_at.isoformat(),
            "age_hours": round(self.age_hours, 4),
            "score": round(self.score, 4),
            "bm25": round(self.bm25, 4),
            "dense": round(self.dense, 4),
        }


@dataclass
class FreshnessResult:
    status: FreshnessStatus
    age_hours: float
    max_age_hours: float
    doc_id: str
    chunk_id: str
    source_system: str = ""

    def as_dict(self) -> dict:
        return {
            "status": self.status.value,
            "age_hours": round(self.age_hours, 4),
            "max_age_hours": self.max_age_hours,
            "doc_id": self.doc_id,
            "chunk_id": self.chunk_id,
            "source_system": self.source_system,
        }


@dataclass
class GroundingResult:
    passed: bool
    query_coverage: float
    answer_coverage: float
    threshold: float
    overlap_tokens: list[str] = field(default_factory=list)

    def as_dict(self) -> dict:
        return {
            "passed": self.passed,
            "query_coverage": round(self.query_coverage, 4),
            "answer_coverage": round(self.answer_coverage, 4),
            "threshold": self.threshold,
            "overlap_tokens": self.overlap_tokens,
        }


@dataclass
class PolicyDecision:
    decision: Decision
    reason: str


@dataclass
class CopilotResult:
    query: str
    decision: Decision
    reason: str
    answer: str
    retrieved: list[Chunk]
    fresh_hits: list[Chunk]
    freshness: list[FreshnessResult]
    grounding: GroundingResult | None
    latency_ms: float
    approx_cost_units: float
    cited_ids: list[str]
    disagreement: dict | None = None
    canary: dict | None = None

    def as_dict(self) -> dict:
        return {
            "query": self.query,
            "decision": self.decision.value,
            "reason": self.reason,
            "answer": self.answer,
            "retrieved_ids": [c.chunk_id for c in self.retrieved],
            "cited_ids": self.cited_ids,
            "ages_hours": [round(c.age_hours, 4) for c in self.retrieved],
            "freshness": [f.as_dict() for f in self.freshness],
            "grounding": self.grounding.as_dict() if self.grounding else None,
            "disagreement": self.disagreement,
            "canary": self.canary,
            "latency_ms": round(self.latency_ms, 3),
            "approx_cost_units": round(self.approx_cost_units, 4),
        }
