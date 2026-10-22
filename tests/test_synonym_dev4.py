"""dev4 set: shape, vocabulary guards (incl. dev3 reuse), must-refuse rows, frozen split."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

import pytest

from ops_copilot.resource_audit import HAND_WRITTEN, audit
from ops_copilot.synonym_dev2 import swapped_in
from ops_copilot.synonym_dev4 import (
    HALVES,
    group_key,
    half,
    load_dev4,
    must_refuse_rows,
    split_dev4,
    summary,
    vocabulary_problems,
)

GOLDEN = Path(__file__).resolve().parents[1] / "data" / "golden" / "questions.jsonl"


def _golden() -> list[dict]:
    return [json.loads(ln) for ln in GOLDEN.read_text(encoding="utf-8").splitlines() if ln.strip()]


def test_dev4_has_44_unique_rows() -> None:
    rows = load_dev4()
    assert len(rows) == 44 and len({r["id"] for r in rows}) == 44
    labels = Counter(r["expect_decision"] for r in rows)
    assert labels["ANSWER"] == 25 and labels["REFUSE_STALE"] == 6 and labels["REFUSE_UNGROUNDED"] == 8


def test_swap_rows_keep_the_golden_label_and_traps_have_none() -> None:
    golden = _golden()
    for r in load_dev4():
        assert ("swap" in r) != ("trap" in r), r["id"]
        if "swap" in r:
            assert swapped_in(r), r["id"]
            assert golden[r["source_index"]]["expect_decision"] == r["expect_decision"], r["id"]
            old = r["swap"].split("->", 1)[0].strip().lower()
            assert old in golden[r["source_index"]]["query"].lower().rstrip("?").split(), r["id"]
            assert old not in r["query"].lower().rstrip("?").split(), r["id"]
        else:
            assert "source_index" not in r


def test_no_heldout_word_no_shared_or_repeated_swap_vocabulary() -> None:
    assert vocabulary_problems() == {}


def test_guard_catches_dev3_reuse_and_repeats_inside_dev4() -> None:
    bad = [
        {"id": "y1", "query": "What is the current checkout p99 slowness?", "expect_decision": "ANSWER",
         "source_index": 0, "swap": "latency -> slowness"},
        {"id": "y2", "query": "What is the checkout sluggishness?", "expect_decision": "ANSWER",
         "source_index": 0, "swap": "latency -> sluggishness"},
        {"id": "y3", "query": "Is the checkout sluggishness flag enabled?", "expect_decision": "ANSWER",
         "source_index": 1, "swap": "feature -> sluggishness"},
    ]
    got = vocabulary_problems(bad)
    assert got["y1"] == ["shared_dev3:slowness"]
    assert got["y2"] == ["repeated_swap:sluggishness"] and got["y3"] == ["repeated_swap:sluggishness"]


def test_split_keeps_every_source_group_in_one_half() -> None:
    rows = load_dev4()
    sp = split_dev4(rows)
    assert set(sp) == {r["id"] for r in rows} and set(sp.values()) == set(HALVES)
    by_group: dict[str, set[str]] = {}
    for r in rows:
        by_group.setdefault(group_key(r), set()).add(sp[r["id"]])
    assert all(len(v) == 1 for v in by_group.values())


def test_split_is_frozen_and_label_balanced() -> None:
    assert len(half("tune")) == 23 and len(half("confirm")) == 21
    s = summary()
    assert s["tune"]["ANSWER"] == 12 and s["confirm"]["ANSWER"] == 13
    for label in {r["expect_decision"] for r in load_dev4()}:
        assert abs(s["tune"].get(label, 0) - s["confirm"].get(label, 0)) <= 3, label
    sp = split_dev4()
    assert (sp["d4-01"], sp["d4-09"], sp["d4-28"], sp["d4-37"]) == ("tune", "confirm", "tune", "confirm")


def test_must_refuse_rows_are_every_refusal_in_each_half() -> None:
    assert len(must_refuse_rows(half("tune"))) == 10
    assert len(must_refuse_rows(half("confirm"))) == 8
    assert all(r["expect_decision"].startswith("REFUSE_") for r in must_refuse_rows(load_dev4()))


def test_a_group_with_mixed_labels_is_rejected() -> None:
    rows = [
        {"id": "z1", "source_index": 0, "query": "q", "expect_decision": "ANSWER", "swap": "a -> b"},
        {"id": "z2", "source_index": 0, "query": "q", "expect_decision": "REFUSE_STALE", "swap": "a -> c"},
    ]
    with pytest.raises(ValueError):
        split_dev4(rows)


def test_dev4_is_in_the_heldout_resource_audit_and_clean() -> None:
    rel = "data/eval/synonym_dev4.jsonl"
    assert rel in HAND_WRITTEN
    assert audit((rel,))[rel] == []
