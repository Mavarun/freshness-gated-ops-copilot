"""Hand-written write-intent eval set: vocabulary, labels, safety, PR #12 baseline."""

from __future__ import annotations

from collections import Counter

import pytest

from ops_copilot.eval import load_golden
from ops_copilot.synonym_split import load_split
from ops_copilot.text import fold_token, tokenize
from ops_copilot.write_eval import (
    load_write_eval,
    pr12_keyword_detector,
    run_pr12_baseline,
    run_write_eval,
)
from ops_copilot import CopilotConfig


@pytest.fixture(scope="module")
def default_run():
    return run_write_eval()


def test_eval_set_shape() -> None:
    rows = load_write_eval()
    assert 40 <= len(rows) <= 50
    assert len({r["id"] for r in rows}) == len(rows)
    labels = Counter(r["label"] for r in rows)
    assert labels["write"] >= 20 and labels["read"] >= 15 and labels["ambiguous"] >= 6
    cats = {r["category"] for r in rows}
    assert {"imperative", "request", "informational", "adversarial", "ambiguous", "backoff"} == cats


def test_eval_set_uses_no_heldout_vocabulary() -> None:
    held = {fold_token(w) for w in load_split()["heldout_words"]}
    leaked = sorted(
        {t for r in load_write_eval() for t in tokenize(r["query"]) if fold_token(t) in held}
    )
    assert leaked == []


def test_eval_set_does_not_reuse_golden_or_perturbed_queries() -> None:
    from ops_copilot.paraphrase_set import load_paraphrase_set

    seen = {g["query"].lower() for g in load_golden()}
    seen |= {r["query"].lower() for r in load_paraphrase_set()}
    assert not {r["query"].lower() for r in load_write_eval()} & seen


def test_default_config_is_safe_on_the_eval_set(default_run) -> None:
    assert default_run["n_spurious_write"] == 0
    assert default_run["precision"] == 1.0
    assert default_run["n_over_asking"] == 0
    assert default_run["clarification_recall"] == 1.0
    assert default_run["exact_action_target"] == default_run["tp"]  # every proposal fully right
    assert default_run["recall"] == pytest.approx(18 / 22)


def test_prototype_backoff_stays_safe_on_the_eval_set() -> None:
    run = run_write_eval(CopilotConfig(embedding_backend="frozen", write_prototype_backoff=True))
    assert run["n_spurious_write"] == 0 and run["precision"] == 1.0
    assert run["recall"] >= 18 / 22


def test_pr12_baseline_reproduces_the_golden_write_rows() -> None:
    for g in load_golden():
        hit = pr12_keyword_detector(g["query"])
        if g["expect_decision"] == "PROPOSE_WRITE":
            assert hit == (g["expect_write_action"], g["expect_write_target"])
        else:
            assert hit is None, g["query"]


def test_pr12_baseline_numbers() -> None:
    base = run_pr12_baseline()
    assert base["tp"] == 3 and base["n_spurious_write"] == 7


def test_committed_artifact_matches_a_fresh_run() -> None:
    import json
    from pathlib import Path

    from ops_copilot.write_eval import run_write_eval_grid

    art = Path(__file__).resolve().parents[1] / "artifacts" / "write_intent_eval.json"
    fresh = json.loads(json.dumps(run_write_eval_grid(), sort_keys=True))
    assert json.loads(art.read_text()) == fresh
