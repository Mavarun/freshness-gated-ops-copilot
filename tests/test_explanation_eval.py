"""The explanation-correctness eval and its committed artifacts."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from ops_copilot.eval import load_golden
from ops_copilot.explain_eval import corpus_truth, load_expectations, run_explanation_eval

ART = Path(__file__).resolve().parents[1] / "artifacts" / "explanation_eval.json"


@pytest.fixture(scope="module")
def run():
    return run_explanation_eval()


def test_expectations_cover_every_golden_refusal() -> None:
    golden = load_golden()
    refusing = {i for i, g in enumerate(golden) if g["expect_decision"] not in ("ANSWER", "PROPOSE_WRITE")}
    exps = load_expectations()
    assert {e["golden_index"] for e in exps} == refusing
    for e in exps:
        assert golden[e["golden_index"]]["query"] == e["query"]


def test_truth_is_computed_from_the_corpus_and_yaml() -> None:
    t = corpus_truth()
    assert t["graf_payments_qps"]["sla_hours"] == 1.0
    assert t["graf_payments_qps"]["age_hours"] == pytest.approx(2.5)
    assert t["rb_redis_maxmemory"]["sla_hours"] == 48.0


def test_golden_explanations_are_all_correct(run) -> None:
    g = run["golden"]
    assert g["n_rows"] == 33 and g["rows_all_correct"] == 33
    assert g["n_checks_correct"] == g["n_checks"]
    assert g["n_schema_ok"] == g["n"]


def test_perturbed_explanations_schema_and_transfer(run) -> None:
    p = run["perturbed"]
    assert p["n"] == 203 and p["n_schema_ok"] == 203
    t = p["transfer"]
    assert t["n_checks_correct"] / t["n_checks"] >= 0.95
    by = t["by_check"]
    for name in ("stale_age_correct", "stale_sla_correct", "bm25_doc_correct", "canary_doc_correct", "pii_doc_correct"):
        assert by[name]["correct"] == by[name]["n"], name


def test_no_explanation_leaks_anything(run) -> None:
    lk = run["leaks"]
    assert lk["n_leaks"] == 0, lk["examples"]
    assert lk["n_probe_queries"] >= 80


def test_write_refusal_explanations(run) -> None:
    w = run["write_refusals"]
    assert w["suggestion_correct"] == w["suggestion_expected"] == 5
    assert w["reason_code_correct"] == 10 and w["with_remediation"] == w["n"]


def test_committed_artifact_matches_a_fresh_run(run) -> None:
    committed = json.loads(ART.read_text())
    assert committed["default"] == json.loads(json.dumps(run, sort_keys=True))
