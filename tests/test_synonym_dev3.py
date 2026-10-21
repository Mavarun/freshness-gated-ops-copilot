"""dev3 set: shape, vocabulary guards, and a frozen split by golden source row."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

import pytest

from ops_copilot.resource_audit import HAND_WRITTEN, audit
from ops_copilot.synonym_dev2 import swapped_in
from ops_copilot.synonym_dev3 import (
    HALVES,
    group_key,
    half,
    load_dev3,
    split_dev3,
    summary,
    vocabulary_problems,
)

GOLDEN = Path(__file__).resolve().parents[1] / "data" / "golden" / "questions.jsonl"


def _golden() -> list[dict]:
    return [json.loads(ln) for ln in GOLDEN.read_text(encoding="utf-8").splitlines() if ln.strip()]


def test_dev3_has_45_unique_rows() -> None:
    rows = load_dev3()
    assert len(rows) == 45 and len({r["id"] for r in rows}) == 45
    labels = Counter(r["expect_decision"] for r in rows)
    assert labels["ANSWER"] == 25 and labels["REFUSE_UNGROUNDED"] == 8


def test_swap_rows_keep_the_golden_label_and_traps_have_none() -> None:
    golden = _golden()
    for r in load_dev3():
        assert ("swap" in r) != ("trap" in r), r["id"]
        if "swap" in r:
            assert swapped_in(r), r["id"]
            assert golden[r["source_index"]]["expect_decision"] == r["expect_decision"], r["id"]
        else:
            assert "source_index" not in r


def test_no_heldout_word_no_shared_or_repeated_swap_vocabulary() -> None:
    assert vocabulary_problems() == {}


def test_guard_catches_dev2_reuse_and_repeats_inside_dev3() -> None:
    bad = [
        {"id": "y1", "query": "What is the current checkout p99 delay?", "expect_decision": "ANSWER",
         "source_index": 0, "swap": "latency -> delay"},
        {"id": "y2", "query": "What is the checkout tardiness?", "expect_decision": "ANSWER",
         "source_index": 0, "swap": "latency -> tardiness"},
        {"id": "y3", "query": "Is the checkout tardiness flag enabled?", "expect_decision": "ANSWER",
         "source_index": 1, "swap": "feature -> tardiness"},
    ]
    got = vocabulary_problems(bad)
    assert got["y1"] == ["shared_dev2:delay"]
    assert got["y2"] == ["repeated_swap:tardiness"] and got["y3"] == ["repeated_swap:tardiness"]


def test_split_keeps_every_source_group_in_one_half() -> None:
    rows = load_dev3()
    sp = split_dev3(rows)
    assert set(sp) == {r["id"] for r in rows} and set(sp.values()) == set(HALVES)
    by_group: dict[str, set[str]] = {}
    for r in rows:
        by_group.setdefault(group_key(r), set()).add(sp[r["id"]])
    assert all(len(v) == 1 for v in by_group.values())


def test_split_is_frozen_and_label_balanced() -> None:
    assert len(half("calib")) == 25 and len(half("confirm")) == 20
    s = summary()
    assert s["calib"]["ANSWER"] == 13 and s["confirm"]["ANSWER"] == 12
    for label in {r["expect_decision"] for r in load_dev3()}:
        # a group of up to three rows may tip a label by its own size
        assert abs(s["calib"].get(label, 0) - s["confirm"].get(label, 0)) <= 3, label
    sp = split_dev3()
    assert (sp["d3-01"], sp["d3-03"], sp["d3-29"], sp["d3-36"]) == ("calib", "confirm", "confirm", "calib")


def test_a_group_with_mixed_labels_is_rejected() -> None:
    rows = [
        {"id": "z1", "source_index": 0, "query": "q", "expect_decision": "ANSWER", "swap": "a -> b"},
        {"id": "z2", "source_index": 0, "query": "q", "expect_decision": "REFUSE_STALE", "swap": "a -> c"},
    ]
    with pytest.raises(ValueError):
        split_dev3(rows)


def test_dev3_is_in_the_heldout_resource_audit_and_clean() -> None:
    rel = "data/eval/synonym_dev3.jsonl"
    assert rel in HAND_WRITTEN
    assert audit((rel,))[rel] == []
