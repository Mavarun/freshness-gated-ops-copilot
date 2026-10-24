"""dev5 set: shape, vocabulary guards (incl. dev4 reuse), must-refuse rows, frozen split."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

import pytest

from ops_copilot.resource_audit import HAND_WRITTEN, audit
from ops_copilot.synonym_dev2 import swapped_in
from ops_copilot.synonym_dev5 import (
    HALVES,
    group_key,
    half,
    load_dev5,
    must_refuse_rows,
    split_dev5,
    summary,
    vocabulary_problems,
)

GOLDEN = Path(__file__).resolve().parents[1] / "data" / "golden" / "questions.jsonl"


def _golden() -> list[dict]:
    return [json.loads(ln) for ln in GOLDEN.read_text(encoding="utf-8").splitlines() if ln.strip()]


def test_dev5_has_44_unique_rows() -> None:
    rows = load_dev5()
    assert len(rows) == 44 and len({r["id"] for r in rows}) == 44
    labels = Counter(r["expect_decision"] for r in rows)
    assert labels["ANSWER"] == 25 and labels["REFUSE_STALE"] == 6 and labels["REFUSE_UNGROUNDED"] == 8
    assert labels["REFUSE_NO_EVIDENCE"] == 2 and sum(labels.values()) == 44


def test_swap_rows_keep_the_golden_label_and_traps_have_none() -> None:
    golden = _golden()
    for r in load_dev5():
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


def test_guard_catches_dev4_reuse_and_repeats_inside_dev5() -> None:
    bad = [
        {"id": "y1", "query": "What is the current checkout p99 responsiveness?", "expect_decision": "ANSWER",
         "source_index": 0, "swap": "latency -> responsiveness"},
        {"id": "y2", "query": "What is the checkout tardiness?", "expect_decision": "ANSWER",
         "source_index": 0, "swap": "latency -> tardiness"},
        {"id": "y3", "query": "Is the checkout tardiness flag enabled?", "expect_decision": "ANSWER",
         "source_index": 1, "swap": "feature -> tardiness"},
    ]
    got = vocabulary_problems(bad)
    assert got["y1"] == ["shared_dev4:responsiveness"]
    assert "repeated_swap:tardiness" in got["y2"] and "repeated_swap:tardiness" in got["y3"]


def test_split_keeps_every_source_group_in_one_half() -> None:
    rows = load_dev5()
    sp = split_dev5(rows)
    assert set(sp) == {r["id"] for r in rows} and set(sp.values()) == set(HALVES)
    by_group: dict[str, set[str]] = {}
    for r in rows:
        by_group.setdefault(group_key(r), set()).add(sp[r["id"]])
    assert all(len(v) == 1 for v in by_group.values())


def test_split_is_frozen_and_label_balanced() -> None:
    assert len(half("tune")) == 24 and len(half("confirm")) == 20
    s = summary()
    assert s["tune"]["ANSWER"] == 13 and s["confirm"]["ANSWER"] == 12
    for label in {r["expect_decision"] for r in load_dev5()}:
        assert abs(s["tune"].get(label, 0) - s["confirm"].get(label, 0)) <= 3, label
    sp = split_dev5()
    assert (sp["d5-01"], sp["d5-03"], sp["d5-37"], sp["d5-38"], sp["d5-39"]) == (
        "tune", "confirm", "tune", "tune", "confirm")


def test_must_refuse_rows_are_every_refusal_in_each_half() -> None:
    assert len(must_refuse_rows(half("tune"))) == 10
    assert len(must_refuse_rows(half("confirm"))) == 8
    assert all(r["expect_decision"].startswith("REFUSE_") for r in must_refuse_rows(load_dev5()))


def test_word_sense_traps_put_one_unknown_word_next_to_corpus_words() -> None:
    traps = {r["id"]: r for r in load_dev5() if "trap" in r}
    assert len(traps) == 6
    assert {"d5-37", "d5-38", "d5-39"} <= set(traps)
    assert all(traps[i]["expect_decision"] == "REFUSE_UNGROUNDED" for i in ("d5-36", "d5-37", "d5-38", "d5-39"))


def test_a_group_with_mixed_labels_is_rejected() -> None:
    rows = [
        {"id": "z1", "source_index": 0, "query": "q", "expect_decision": "ANSWER", "swap": "a -> b"},
        {"id": "z2", "source_index": 0, "query": "q", "expect_decision": "REFUSE_STALE", "swap": "a -> c"},
    ]
    with pytest.raises(ValueError):
        split_dev5(rows)


def test_dev5_is_in_the_heldout_resource_audit_and_clean() -> None:
    rel = "data/eval/synonym_dev5.jsonl"
    assert rel in HAND_WRITTEN
    assert audit((rel,))[rel] == []
