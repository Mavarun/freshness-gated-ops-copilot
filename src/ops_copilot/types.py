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
    REFUSE_BUDGET = "REFUSE_BUDGET"
    REFUSE_CANARY = "REFUSE_CANARY"
    REFUSE_PII = "REFUSE_PII"
    PROPOSE_WRITE = "PROPOSE_WRITE"
    REFUSE_AMBIGUOUS_WRITE = "REFUSE_AMBIGUOUS_WRITE"


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
    # Semantic grounding backoff (embeddings): query terms counted as supported
    # because a cited sentence cleared the cosine threshold, and that cosine.
    semantic_rescued: list[str] = field(default_factory=list)
    semantic_similarity: float | None = None
    # Answer-support model (qa_translation): "query<-evidence" word pairs the
    # outside-trained translation model counted as support.
    translation_rescued: list[str] = field(default_factory=list)
    # Passage-level answer support (passage_support): missing query words the
    # pair classifier vouched for, as "query<-closest evidence word", and the
    # classifier's probability for the chunk it read.
    passage_rescued: list[str] = field(default_factory=list)
    passage_probability: float | None = None

    def as_dict(self) -> dict:
        return {
            "passed": self.passed,
            "query_coverage": round(self.query_coverage, 4),
            "answer_coverage": round(self.answer_coverage, 4),
            "threshold": self.threshold,
            "overlap_tokens": self.overlap_tokens,
            "semantic_rescued": self.semantic_rescued,
            "semantic_similarity": (
                None if self.semantic_similarity is None else round(self.semantic_similarity, 4)
            ),
            "translation_rescued": self.translation_rescued,
            "passage_rescued": self.passage_rescued,
            "passage_probability": (
                None if self.passage_probability is None else round(self.passage_probability, 4)
            ),
        }


@dataclass
class PolicyDecision:
    decision: Decision
    reason: str
    # Structured refusal explanation (explain.RefusalExplanation.as_dict());
    # None for ANSWER and PROPOSE_WRITE.
    explanation: dict | None = None


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
    session_id: str | None = None
    session_spent_before: float = 0.0
    session_spent_after: float = 0.0
    session_budget: float | None = None
    canary: dict | None = None
    proposed_write: dict | None = None
    pii_detected: bool = False
    redactions_count: int = 0
    pii: dict | None = None
    # Write-intent parse trace (status, mood, verb, target, confidence).
    write_intent: dict | None = None
    # Structured refusal explanation (refusals only).
    explanation: dict | None = None

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
            "latency_ms": round(self.latency_ms, 3),
            "approx_cost_units": round(self.approx_cost_units, 4),
            "session_id": self.session_id,
            "session_spent_before": round(self.session_spent_before, 4),
            "session_spent_after": round(self.session_spent_after, 4),
            "session_budget": self.session_budget,
            "canary": self.canary,
            "proposed_write": self.proposed_write,
            "pii_detected": self.pii_detected,
            "redactions_count": self.redactions_count,
            "pii": self.pii,
            "write_intent": self.write_intent,
            "explanation": self.redacted_explanation(),
        }

    def boundary_dict(self) -> dict:
        """``as_dict`` with user-derived fields redacted, for traces and the API.

        ``query``, refusal ``reason``, ``write_intent`` and ``proposed_write``
        echo user text; a pasted secret, e-mail or canary token is replaced
        with ``[redacted:<kind>]`` (and its tokenizer fragments with
        ``[redacted]``). ``boundary_redactions`` counts the replacements.
        """
        from ops_copilot.explain_redact import redact_boundary

        out, n = redact_boundary(self.as_dict(), query=self.query)
        out["boundary_redactions"] = n
        return out

    def redacted_explanation(self) -> dict | None:
        """The explanation after a boundary redaction pass against the raw query."""
        from ops_copilot.explain_redact import redact_explanation

        out, _ = redact_explanation(self.explanation, context=(self.query,))
        return out
