from __future__ import annotations

from ops_copilot import Copilot
from ops_copilot.eval import load_golden, run_comparison, run_eval
from ops_copilot.disagreement_compare import run_disagreement_comparison
from ops_copilot.types import Decision


def test_golden_set_covers_all_decisions() -> None:
    cases = load_golden()
    assert len(cases) >= 20
    labels = {c["expect_decision"] for c in cases}
    assert labels == {d.value for d in Decision}


def test_eval_metrics_sane(copilot: Copilot) -> None:
    report = run_eval(copilot)
    assert report.n >= 20
    assert 0.0 <= report.refusal_precision <= 1.0
    assert 0.0 <= report.refusal_recall <= 1.0
    assert 0.0 <= report.answer_grounding_rate <= 1.0
    assert report.p50_latency_ms <= report.p95_latency_ms
    # Hiring bar: we must refuse the cases labeled must-refuse.
    assert report.refusal_recall == 1.0
    # Every ANSWER we emit must have passed the grounding gate.
    assert report.answer_grounding_rate == 1.0


def test_decision_accuracy_is_majority_correct(copilot: Copilot) -> None:
    report = run_eval(copilot)
    # Exact-label accuracy should stay high on this frozen corpus.
    assert report.decision_accuracy >= 0.85


def test_comparison_has_flips(copilot: Copilot) -> None:
    """Per-source SLAs must change at least one decision vs global-only."""
    comparison = run_comparison()
    assert comparison.per_source_report.n == comparison.global_report.n
    assert comparison.per_source_report.n >= 24
    assert len(comparison.flips) >= 2
    # Per-source labels should be exact on the crafted set.
    assert comparison.per_source_report.decision_accuracy == 1.0
    assert comparison.global_report.decision_accuracy == 1.0


def test_disagreement_comparison_has_flips() -> None:
    comparison = run_disagreement_comparison()
    assert comparison.dual_report.n == comparison.bm25_only_report.n
    assert comparison.dual_report.n >= 30
    assert len(comparison.flips) >= 4
    assert comparison.dual_report.decision_accuracy == 1.0
    assert comparison.bm25_only_report.decision_accuracy == 1.0
    assert comparison.dual_report.disagreement_rate > 0.0
