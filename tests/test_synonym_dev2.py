"""dev2 calibration set: shape, vocabulary guards and a frozen calib / confirm split."""

from __future__ import annotations

from collections import Counter

from ops_copilot.resource_audit import HAND_WRITTEN
from ops_copilot.synonym_dev2 import HALVES, half, load_dev2, split_dev2, swapped_in, vocabulary_problems


def test_dev2_has_43_unique_rows_with_valid_labels() -> None:
    rows = load_dev2()
    assert len(rows) == 43
    assert len({r["id"] for r in rows}) == 43
    labels = Counter(r["expect_decision"] for r in rows)
    assert labels["ANSWER"] == 20
    assert set(labels) <= {
        "ANSWER", "REFUSE_STALE", "REFUSE_UNGROUNDED", "REFUSE_NO_EVIDENCE",
        "REFUSE_CANARY", "REFUSE_PII", "PROPOSE_WRITE",
    }


def test_every_row_is_a_swap_or_a_new_trap() -> None:
    for r in load_dev2():
        assert ("swap" in r) != ("trap" in r), r["id"]
        if "swap" in r:
            assert "source_index" in r and swapped_in(r), r["id"]


def test_swap_rows_keep_the_golden_label() -> None:
    import json
    from pathlib import Path

    golden = [
        json.loads(ln)
        for ln in (Path(__file__).resolve().parents[1] / "data/golden/questions.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()
        if ln.strip()
    ]
    for r in load_dev2():
        if "swap" in r:
            assert golden[r["source_index"]]["expect_decision"] == r["expect_decision"], r["id"]


def test_no_heldout_word_and_no_shared_swap_vocabulary() -> None:
    assert vocabulary_problems() == {}


def test_guard_catches_a_heldout_word_and_a_shared_swap() -> None:
    bad = [
        {"id": "x1", "query": "What is the checkout lag?", "expect_decision": "ANSWER", "swap": "latency -> lag"},
        {"id": "x2", "query": "What is the condition of payments-api?", "expect_decision": "ANSWER",
         "swap": "status -> condition"},
        {"id": "x3", "query": "How many requests hit checkout?", "expect_decision": "ANSWER", "trap": "t"},
    ]
    got = vocabulary_problems(bad)
    assert "heldout:lag" in got["x1"]
    assert got["x2"] == ["shared_swap:condition"]
    assert got["x3"] == ["heldout:request"]


def test_split_is_frozen_stratified_and_complete() -> None:
    rows = load_dev2()
    sp = split_dev2(rows)
    assert set(sp) == {r["id"] for r in rows}
    assert set(sp.values()) == set(HALVES)
    for label in {r["expect_decision"] for r in rows}:
        c = Counter(sp[r["id"]] for r in rows if r["expect_decision"] == label)
        assert abs(c["calib"] - c["confirm"]) <= 1, label
    assert len(half("calib")) == 22 and len(half("confirm")) == 21
    # Frozen: changing the salt or the rows would silently move rows across halves.
    assert sp["d2-01"] == "calib" and sp["d2-02"] == "confirm" and sp["d2-30"] == "calib"


def test_dev2_is_covered_by_the_heldout_resource_audit() -> None:
    assert "data/eval/synonym_dev2.jsonl" in HAND_WRITTEN
