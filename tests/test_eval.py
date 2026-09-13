from __future__ import annotations

from ops_copilot import Copilot
from ops_copilot.eval import load_golden, run_eval
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
    assert report.refusal_recall == 1.0
    assert report.answer_grounding_rate == 1.0


def test_decision_accuracy_is_majority_correct(copilot: Copilot) -> None:
    report = run_eval(copilot)
    assert report.decision_accuracy >= 0.85
