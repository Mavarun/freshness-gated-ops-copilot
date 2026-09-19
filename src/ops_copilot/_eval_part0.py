"""Golden-set runner and refusal / grounding / latency metrics.

Supports a dual-mode comparison: global-only SLA vs per-source SLAs on the
same corpus and golden set. Cases may carry ``expect_decision`` (per-source
default) and optional ``expect_decision_global`` for the global-only run.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import pandas as pd

from ops_copilot.config import CopilotConfig
from ops_copilot.pipeline import Copilot
from ops_copilot.trace import TraceWriter
from ops_copilot.types import CopilotResult, Decision

DEFAULT_GOLDEN = (
    Path(__file__).resolve().parents[2] / "data" / "golden" / "questions.jsonl"
)


def _is_refuse(label: str) -> bool:
    return str(label).startswith("REFUSE_")


@dataclass
class CaseScore:
    query: str
    expect_decision: str
    actual_decision: str
    note: str
    match: bool
    must_refuse: bool
    did_refuse: bool
    latency_ms: float
    grounding_passed: bool | None
    cited_ids: list[str] = field(default_factory=list)
    reason: str = ""
    mode: str = "per_source"
    disagreed: bool | None = None
    jaccard: float | None = None
    session_id: str | None = None
    budget_refused: bool = False


@dataclass
class EvalReport:
    scores: list[CaseScore]
    n: int
    decision_accuracy: float
    refusal_precision: float
    refusal_recall: float
    answer_grounding_rate: float
    p50_latency_ms: float
    p95_latency_ms: float
    confusion: dict[str, int]
    mode: str = "per_source"
    disagreement_rate: float = 0.0
    n_disagreed: int = 0
    budget_refuse_rate: float = 0.0
    n_budget_refused: int = 0

    def as_dict(self) -> dict:
        return {
            "mode": self.mode,
            "n": self.n,
            "decision_accuracy": self.decision_accuracy,
            "refusal_precision": self.refusal_precision,
            "refusal_recall": self.refusal_recall,
            "answer_grounding_rate": self.answer_grounding_rate,
            "disagreement_rate": self.disagreement_rate,
            "n_disagreed": self.n_disagreed,
            "budget_refuse_rate": self.budget_refuse_rate,
            "n_budget_refused": self.n_budget_refused,
            "p50_latency_ms": self.p50_latency_ms,
            "p95_latency_ms": self.p95_latency_ms,
            "confusion": self.confusion,
        }

    def to_frame(self) -> pd.DataFrame:
        return pd.DataFrame(
            [
                {
                    "query": s.query,
                    "expect": s.expect_decision,
                    "actual": s.actual_decision,
                    "match": s.match,
                    "latency_ms": round(s.latency_ms, 3),
                    "cited_ids": ",".join(s.cited_ids),
                    "note": s.note,
                }
                for s in self.scores
            ]
        )


@dataclass
class ComparisonReport:
    """Side-by-side global-only vs per-source metrics on the same golden set."""

    global_report: EvalReport
    per_source_report: EvalReport
    flips: list[dict]

    def as_dict(self) -> dict:
