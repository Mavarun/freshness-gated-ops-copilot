"""BM25-only vs dual disagreement routing comparison (offline eval)."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from ops_copilot.config import CopilotConfig
from ops_copilot.eval import CaseScore, EvalReport, load_golden, _is_refuse, _metrics
from ops_copilot.pipeline import Copilot
from ops_copilot.types import CopilotResult


@dataclass
class DisagreementComparisonReport:
    """BM25-only (gate off) vs dual-retriever disagreement routing."""

    bm25_only_report: EvalReport
    dual_report: EvalReport
    flips: list[dict]

    def as_dict(self) -> dict:
        return {
            "bm25_only": self.bm25_only_report.as_dict(),
            "dual_disagreement": self.dual_report.as_dict(),
            "decision_flips": self.flips,
            "n_flips": len(self.flips),
        }


def run_disagreement_comparison(
    *,
    golden_path: str | Path | None = None,
    corpus_path: str | Path | None = None,
) -> DisagreementComparisonReport:
    shared: dict = {}
    if corpus_path is not None:
        shared["path"] = corpus_path

    bm25_bot = Copilot(
        config=CopilotConfig(use_disagreement_gate=False, use_source_slas=True),
        **shared,
    )
    dual_bot = Copilot(
        config=CopilotConfig(use_disagreement_gate=True, use_source_slas=True),
        **shared,
    )

    cases = load_golden(golden_path)
    bm25_scores: list[CaseScore] = []
    dual_scores: list[CaseScore] = []
    flips: list[dict] = []

    for case in cases:
        q = case["query"]
        sid = case.get("session_id")
        session_id = str(sid) if sid else None
        if session_id and "seed_session_spent" in case:
            spent = float(case["seed_session_spent"])
            bm25_bot.ledger.seed(session_id, spent)
            dual_bot.ledger.seed(session_id, spent)
        bm25_res: CopilotResult = bm25_bot.ask(q, session_id=session_id)
        dual_res: CopilotResult = dual_bot.ask(q, session_id=session_id)
        expect_bm25 = str(case.get("expect_decision_bm25_only") or case["expect_decision"])
        expect_dual = str(case["expect_decision"])

        def _score(res: CopilotResult, expect: str, mode: str) -> CaseScore:
            actual = res.decision.value
            disagreed = None
            jaccard = None
            if res.disagreement is not None:
                disagreed = not bool(res.disagreement.get("agreed", True))
                jaccard = res.disagreement.get("jaccard")
            return CaseScore(
                query=q,
                expect_decision=expect,
                actual_decision=actual,
                note=str(case.get("note", "")),
                match=actual == expect,
                must_refuse=_is_refuse(expect),
                did_refuse=_is_refuse(actual),
                latency_ms=res.latency_ms,
                grounding_passed=(
                    None if res.grounding is None else res.grounding.passed
                ),
                cited_ids=res.cited_ids,
                reason=res.reason,
                mode=mode,
                disagreed=disagreed,
                jaccard=jaccard,
                session_id=session_id,
                budget_refused=actual == "REFUSE_BUDGET",
            )

        b = _score(bm25_res, expect_bm25, "bm25_only")
        d = _score(dual_res, expect_dual, "dual_disagreement")
        bm25_scores.append(b)
        dual_scores.append(d)
        jaccard = None
        if dual_res.disagreement is not None:
            jaccard = dual_res.disagreement.get("jaccard")
        if b.actual_decision != d.actual_decision:
            flips.append(
                {
                    "query": q,
                    "bm25_only_decision": b.actual_decision,
                    "dual_decision": d.actual_decision,
                    "note": d.note or b.note,
                    "jaccard": jaccard,
                }
            )

    bm25_report = _metrics(bm25_scores, "bm25_only")
    dual_report = _metrics(dual_scores, "dual_disagreement")
    n_disagreed = sum(1 for s in dual_scores if s.actual_decision == "REFUSE_DISAGREE")
    try:
        dual_report.disagreement_rate = n_disagreed / dual_report.n if dual_report.n else 0.0
        dual_report.n_disagreed = n_disagreed
    except Exception:
        pass

    return DisagreementComparisonReport(
        bm25_only_report=bm25_report,
        dual_report=dual_report,
        flips=flips,
    )


def render_disagreement_comparison_markdown(
    comparison: DisagreementComparisonReport,
) -> str:
    b = comparison.bm25_only_report.as_dict()
    d = comparison.dual_report.as_dict()
    lines = [
        "# Freshness-gated ops copilot — BM25-only vs dual disagreement",
        "",
        "Frozen clock: `2026-09-13T00:00:00+00:00`. Same corpus, same golden set.",
        "",
        "## Metrics comparison",
        "",
        "| Metric | BM25-only (gate off) | Dual (disagreement gate) |",
        "| --- | ---: | ---: |",
        "| cases | {bn} | {dn} |".format(bn=b["n"], dn=d["n"]),
        "| decision_accuracy | {ba:.3f} | {da:.3f} |".format(
            ba=b["decision_accuracy"], da=d["decision_accuracy"]
        ),
        "| disagreement_rate | {br:.3f} | {dr:.3f} |".format(
            br=b.get("disagreement_rate", 0.0),
            dr=d.get("disagreement_rate", 0.0),
        ),
        "",
        "## Decision flips (n={n})".format(n=len(comparison.flips)),
        "",
        "| Query | BM25-only | Dual | Note |",
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
            "| {q} | `{b}` | `{d}` | {n} |".format(
                q=q,
                b=flip["bm25_only_decision"],
                d=flip["dual_decision"],
                n=note,
            )
        )
    if not comparison.flips:
        lines.append("| *(none)* | — | — | — |")
    lines.append("")
    return "\n".join(lines)
