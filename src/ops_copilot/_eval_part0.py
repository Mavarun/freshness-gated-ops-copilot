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

from ops_copilot.canary import canary_detection_metrics
from ops_copilot.pii_redact import pii_detection_metrics
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
    expect_canary_leak: bool | None = None
    actual_canary_leak: bool | None = None
    propose_write: bool = False
    expect_pii: bool | None = None
    actual_pii: bool | None = None


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
    canary_precision: float = 0.0
    canary_recall: float = 0.0
    canary_f1: float = 0.0
    n_canary_labeled: int = 0
    propose_write_rate: float = 0.0
    n_propose_write: int = 0
    pii_precision: float = 0.0
    pii_recall: float = 0.0
    pii_f1: float = 0.0
    n_pii_labeled: int = 0

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
            "canary_precision": self.canary_precision,
            "canary_recall": self.canary_recall,
            "canary_f1": self.canary_f1,
            "n_canary_labeled": self.n_canary_labeled,
            "propose_write_rate": self.propose_write_rate,
            "n_propose_write": self.n_propose_write,
            "pii_precision": self.pii_precision,
            "pii_recall": self.pii_recall,
            "pii_f1": self.pii_f1,
            "n_pii_labeled": self.n_pii_labeled,
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
