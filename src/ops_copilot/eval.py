"""Golden-set runner and refusal / grounding / latency metrics."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import pandas as pd

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

    def as_dict(self) -> dict:
        return {
            "n": self.n,
            "decision_accuracy": self.decision_accuracy,
            "refusal_precision": self.refusal_precision,
            "refusal_recall": self.refusal_recall,
            "answer_grounding_rate": self.answer_grounding_rate,
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


def load_golden(path: str | Path | None = None) -> list[dict]:
    src = Path(path) if path else DEFAULT_GOLDEN
    cases: list[dict] = []
    with src.open(encoding="utf-8") as handle:
        for line_no, raw in enumerate(handle, start=1):
            line = raw.strip()
            if not line:
                continue
            row = json.loads(line)
            missing = {"query", "expect_decision"} - set(row)
            if missing:
                raise ValueError(f"{src}:{line_no}: missing {sorted(missing)}")
            row.setdefault("note", "")
            cases.append(row)
    if len(cases) < 1:
        raise ValueError(f"golden set is empty: {src}")
    return cases


def _metrics(scores: list[CaseScore]) -> EvalReport:
    n = len(scores)
    acc = sum(1 for s in scores if s.match) / n if n else 0.0
    must = [s for s in scores if s.must_refuse]
    refused = [s for s in scores if s.did_refuse]
    tp = [s for s in refused if s.must_refuse]
    precision = (len(tp) / len(refused)) if refused else 0.0
    recall = (len(tp) / len(must)) if must else 0.0
    answered = [s for s in scores if s.actual_decision == Decision.ANSWER.value]
    grounded = [s for s in answered if s.grounding_passed]
    grind = (len(grounded) / len(answered)) if answered else 0.0
    lat = np.array([s.latency_ms for s in scores], dtype=float)
    p50 = float(np.percentile(lat, 50)) if n else 0.0
    p95 = float(np.percentile(lat, 95)) if n else 0.0
    confusion: dict[str, int] = {}
    for s in scores:
        key = f"{s.expect_decision}->{s.actual_decision}"
        confusion[key] = confusion.get(key, 0) + 1
    return EvalReport(
        scores=scores,
        n=n,
        decision_accuracy=acc,
        refusal_precision=precision,
        refusal_recall=recall,
        answer_grounding_rate=grind,
        p50_latency_ms=p50,
        p95_latency_ms=p95,
        confusion=confusion,
    )


def run_eval(
    copilot: Copilot | None = None,
    *,
    golden_path: str | Path | None = None,
    trace_path: str | Path | None = None,
) -> EvalReport:
    bot = copilot or Copilot()
    cases = load_golden(golden_path)
    tracer = TraceWriter(trace_path) if trace_path is not None else None
    if tracer:
        tracer.clear()
    scores: list[CaseScore] = []
    for case in cases:
        result: CopilotResult = bot.ask(case["query"])
        expect = str(case["expect_decision"])
        actual = result.decision.value
        score = CaseScore(
            query=case["query"],
            expect_decision=expect,
            actual_decision=actual,
            note=str(case.get("note", "")),
            match=actual == expect,
            must_refuse=_is_refuse(expect),
            did_refuse=_is_refuse(actual),
            latency_ms=result.latency_ms,
            grounding_passed=None if result.grounding is None else result.grounding.passed,
            cited_ids=result.cited_ids,
            reason=result.reason,
        )
        scores.append(score)
        if tracer:
            tracer.write(
                result,
                extra={"expect_decision": expect, "match": score.match, "note": score.note},
            )
    return _metrics(scores)


def render_markdown(report: EvalReport) -> str:
    m = report.as_dict()
    lines = [
        "# Freshness-gated ops copilot — golden eval",
        "",
        "Frozen clock: `2026-09-13T00:00:00+00:00`. SLA: `max_age_hours=48`.",
        "",
        "## Summary metrics",
        "",
        "| Metric | Value |",
        "| --- | ---: |",
        f"| cases | {m['n']} |",
        f"| decision_accuracy | {m['decision_accuracy']:.3f} |",
        f"| refusal_precision | {m['refusal_precision']:.3f} |",
        f"| refusal_recall | {m['refusal_recall']:.3f} |",
        f"| answer_grounding_rate | {m['answer_grounding_rate']:.3f} |",
        f"| p50_latency_ms | {m['p50_latency_ms']:.2f} |",
        f"| p95_latency_ms | {m['p95_latency_ms']:.2f} |",
        "",
        "## Confusion (expect → actual)",
        "",
        "| Pair | Count |",
        "| --- | ---: |",
    ]
    for key, count in sorted(report.confusion.items()):
        lines.append(f"| `{key}` | {count} |")
    lines.extend(["", "## Cases", ""])
    frame = report.to_frame()
    cols = ["query", "expect", "actual", "match", "latency_ms", "cited_ids", "note"]
    lines.append("| " + " | ".join(cols) + " |")
    lines.append("| " + " | ".join("---" for _ in cols) + " |")
    for _, row in frame.iterrows():
        cells = []
        for col in cols:
            val = str(row[col]).replace("|", "/")
            if col == "query" and len(val) > 72:
                val = val[:69] + "..."
            cells.append(val)
        lines.append("| " + " | ".join(cells) + " |")
    lines.append("")
    return "\n".join(lines)
