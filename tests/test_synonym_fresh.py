"""Fresh hand-written synonym set: separate vocabulary, golden labels, pinned result."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from ops_copilot.eval import load_golden
from ops_copilot.fresh_synonym_eval import load_fresh, run_fresh_eval, vocabulary_overlap

ART = Path(__file__).resolve().parents[1] / "artifacts" / "synonym_fresh_eval.json"


@pytest.fixture(scope="module")
def result() -> dict:
    return run_fresh_eval()


def test_rows_keep_their_golden_label_and_are_new_queries() -> None:
    golden = load_golden()
    rows = load_fresh()
    assert len(rows) == 26 and len({r["id"] for r in rows}) == 26
    clean = {g["query"] for g in golden}
    for r in rows:
        assert r["expect_decision"] == golden[r["source_index"]]["expect_decision"], r["id"]
        assert r["query"] not in clean


def test_no_swapped_word_comes_from_the_perturbation_vocabulary() -> None:
    assert vocabulary_overlap(load_fresh()) == {}


def test_backoff_helps_general_english_a_little_and_stays_safe(result: dict) -> None:
    off = result["configs"]["default (word-vector backoff off; = PR #14)"]
    on = result["configs"]["+ word-vector backoff (calibrated)"]
    assert off["n"] - len(off["wrong"]) == 7 and on["n"] - len(on["wrong"]) == 10
    fixed = {r for r, d in on["decisions"].items() if d != off["decisions"][r]}
    assert fixed == {"f10", "f14", "f21"}
    for r in result["configs"].values():
        assert r["n_fail_open"] == r["n_spurious_write"] == r["n_raw_pii_outputs"] == 0


def test_artifact_matches_a_fresh_run(result: dict) -> None:
    art = json.loads(ART.read_text(encoding="utf-8"))
    assert {k: v["decisions"] for k, v in art["configs"].items()} == {
        k: v["decisions"] for k, v in result["configs"].items()
    }
