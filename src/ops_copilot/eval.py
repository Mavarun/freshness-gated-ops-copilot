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

    def as_dict(self) -> dict:
        return {
            "mode": self.mode,
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


@dataclass
class ComparisonReport:
    """Side-by-side global-only vs per-source metrics on the same golden set."""

    global_report: EvalReport
    per_source_report: EvalReport
    flips: list[dict]

    def as_dict(self) -> dict:
        return {
            "global_only": self.global_report.as_dict(),
            "per_source": self.per_source_report.as_dict(),
            "decision_flips": self.flips,
            "n_flips": len(self.flips),
        }


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


def _metrics(scores: list[CaseScore], mode: str) -> EvalReport:
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
        mode=mode,
    )


def _expect_for_mode(case: dict, mode: str) -> str:
    if mode == "global_only":
        return str(case.get("expect_decision_global") or case["expect_decision"])
    return str(case["expect_decision"])


def run_eval(
    copilot: Copilot | None = None,
    *,
    golden_path: str | Path | None = None,
    trace_path: str | Path | None = None,
    mode: str | None = None,
) -> EvalReport:
    bot = copilot or Copilot()
    resolved_mode = mode or (
        "per_source" if bot.config.use_source_slas else "global_only"
    )
    cases = load_golden(golden_path)
    tracer = TraceWriter(trace_path) if trace_path is not None else None
    if tracer:
        tracer.clear()
    scores: list[CaseScore] = []
    for case in cases:
        result: CopilotResult = bot.ask(case["query"])
        expect = _expect_for_mode(case, resolved_mode)
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
            mode=resolved_mode,
        )
        scores.append(score)
        if tracer:
            tracer.write(
                result,
                extra={
                    "expect_decision": expect,
                    "match": score.match,
                    "note": score.note,
                    "mode": resolved_mode,
                },
            )
    return _metrics(scores, resolved_mode)


def run_comparison(
    *,
    golden_path: str | Path | None = None,
    corpus_path: str | Path | None = None,
    trace_path: str | Path | None = None,
) -> ComparisonReport:
    """Run the golden set twice: global-only SLA vs per-source SLAs."""
    shared_kwargs: dict = {}
    if corpus_path is not None:
        shared_kwargs["path"] = corpus_path

    global_bot = Copilot(
        config=CopilotConfig(use_source_slas=False, max_age_hours=48.0),
        **shared_kwargs,
    )
    per_bot = Copilot(
        config=CopilotConfig(use_source_slas=True, max_age_hours=48.0),
        **shared_kwargs,
    )

    global_report = run_eval(
        global_bot,
        golden_path=golden_path,
        mode="global_only",
    )
    per_report = run_eval(
        per_bot,
        golden_path=golden_path,
        trace_path=trace_path,
        mode="per_source",
    )

    flips: list[dict] = []
    for g, p in zip(global_report.scores, per_report.scores, strict=True):
        if g.actual_decision != p.actual_decision:
            flips.append(
                {
                    "query": g.query,
                    "global_decision": g.actual_decision,
                    "per_source_decision": p.actual_decision,
                    "note": p.note or g.note,
                }
            )
    return ComparisonReport(
        global_report=global_report,
        per_source_report=per_report,
        flips=flips,
    )


def render_markdown(report: EvalReport) -> str:
    m = report.as_dict()
    sla_line = (
        "Frozen clock: `2026-09-13T00:00:00+00:00`. "
        "Mode: **per-source SLAs** (see `config/source_slas.yaml`)."
        if report.mode == "per_source"
        else "Frozen clock: `2026-09-13T00:00:00+00:00`. "
        "Mode: **global-only** `max_age_hours=48`."
    )
    lines = [
        "# Freshness-gated ops copilot — golden eval",
        "",
        sla_line,
        "",
        "## Summary metrics",
        "",
        "| Metric | Value |",
        "| --- | ---: |",
        f"| mode | {m['mode']} |",
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


def render_comparison_markdown(comparison: ComparisonReport) -> str:
    g = comparison.global_report.as_dict()
    p = comparison.per_source_report.as_dict()
    lines = [
        "# Freshness-gated ops copilot — global vs per-source SLA",
        "",
        "Frozen clock: `2026-09-13T00:00:00+00:00`. Same corpus, same golden set.",
        "",
        "## Metrics comparison",
        "",
        "| Metric | Global-only (48h) | Per-source SLAs |",
        "| --- | ---: | ---: |",
        f"| cases | {g['n']} | {p['n']} |",
        f"| decision_accuracy | {g['decision_accuracy']:.3f} | {p['decision_accuracy']:.3f} |",
        f"| refusal_precision | {g['refusal_precision']:.3f} | {p['refusal_precision']:.3f} |",
        f"| refusal_recall | {g['refusal_recall']:.3f} | {p['refusal_recall']:.3f} |",
        f"| answer_grounding_rate | {g['answer_grounding_rate']:.3f} | {p['answer_grounding_rate']:.3f} |",
        f"| p50_latency_ms | {g['p50_latency_ms']:.2f} | {p['p50_latency_ms']:.2f} |",
        f"| p95_latency_ms | {g['p95_latency_ms']:.2f} | {p['p95_latency_ms']:.2f} |",
        "",
        f"## Decision flips (n={len(comparison.flips)})",
        "",
        "Queries where the two modes emit different decisions — the empirical",
        "evidence that per-source SLAs change refusal behaviour on a fixed corpus.",
        "",
        "| Query | Global-only | Per-source | Note |",
        "| --- | --- | --- | --- |",
    ]
    for flip in comparison.flips:
        q = flip["query"]
        if len(q) > 56:
            q = q[:53] + "..."
        note = str(flip.get("note", "")).replace("|", "/")
        if len(note) > 48:
            note = note[:45] + "..."
        lines.append(
            f"| {q} | `{flip['global_decision']}` | "
            f"`{flip['per_source_decision']}` | {note} |"
        )
    if not comparison.flips:
        lines.append("| *(none)* | — | — | — |")
    lines.append("")
    lines.append("## Per-source confusion")
    lines.append("")
    lines.append("| Pair | Count |")
    lines.append("| --- | ---: |")
    for key, count in sorted(comparison.per_source_report.confusion.items()):
        lines.append(f"| `{key}` | {count} |")
    lines.append("")
    lines.append("## Global-only confusion")
    lines.append("")
    lines.append("| Pair | Count |")
    lines.append("| --- | ---: |")
    for key, count in sorted(comparison.global_report.confusion.items()):
        lines.append(f"| `{key}` | {count} |")
    lines.append("")
    return "\n".join(lines)
