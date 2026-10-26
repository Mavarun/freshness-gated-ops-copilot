"""dev6 set: shape, vocabulary guards (incl. dev5 reuse), must-refuse rows, held-out audit."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

from ops_copilot.resource_audit import HAND_WRITTEN, audit
from ops_copilot.synonym_dev2 import swapped_in
from ops_copilot.synonym_dev6 import load_dev6, must_refuse_rows, summary, vocabulary_problems

GOLDEN = Path(__file__).resolve().parents[1] / "data" / "golden" / "questions.jsonl"


def _golden() -> list[dict]:
    return [json.loads(ln) for ln in GOLDEN.read_text(encoding="utf-8").splitlines() if ln.strip()]


def test_dev6_has_45_unique_rows_with_the_documented_labels() -> None:
    rows = load_dev6()
    assert len(rows) == 45 and len({r["id"] for r in rows}) == 45
    assert summary() == {
        "ANSWER": 24, "PROPOSE_WRITE": 1, "REFUSE_CANARY": 1, "REFUSE_NO_EVIDENCE": 2,
        "REFUSE_PII": 1, "REFUSE_STALE": 5, "REFUSE_UNGROUNDED": 11,
    }


def test_swap_rows_keep_the_golden_label_and_change_exactly_one_word() -> None:
    golden = _golden()
    for r in load_dev6():
        assert ("swap" in r) != ("trap" in r), r["id"]
        if "trap" in r:
            assert "source_index" not in r
            continue
        g = golden[r["source_index"]]
        assert g["expect_decision"] == r["expect_decision"], r["id"]
        old, new = (p.strip() for p in r["swap"].split("->", 1))
        assert swapped_in(r), r["id"]
        assert r["query"] == g["query"].replace(old, new, 1), r["id"]


def test_no_heldout_word_no_shared_or_repeated_swap_vocabulary() -> None:
    assert vocabulary_problems() == {}


def test_guard_catches_dev5_reuse_heldout_words_and_repeats() -> None:
    bad = [
        {"id": "y1", "source_index": 0, "query": "What is the current checkout p99 turnaround?",
         "expect_decision": "ANSWER", "swap": "latency -> turnaround"},
        {"id": "y2", "source_index": 45, "query": "How do I reboot the checkout-api service?",
         "expect_decision": "REFUSE_UNGROUNDED", "swap": "restart -> reboot"},
        {"id": "y3", "source_index": 0, "query": "What is the current checkout p99 tardiness?",
         "expect_decision": "ANSWER", "swap": "latency -> tardiness"},
        {"id": "y4", "source_index": 6, "query": "What is the Redis checkout-pool tardiness?",
         "expect_decision": "ANSWER", "swap": "utilization -> tardiness"},
    ]
    got = vocabulary_problems(bad)
    assert "shared_dev5:turnaround" in got["y1"]
    assert "heldout:reboot" in got["y2"]
    assert "repeated_swap:tardiness" in got["y3"] and "repeated_swap:tardiness" in got["y4"]


def test_must_refuse_rows_are_every_refusal() -> None:
    mr = must_refuse_rows(load_dev6())
    assert len(mr) == 20
    assert all(r["expect_decision"].startswith("REFUSE_") for r in mr)


def test_word_sense_traps_are_refusals_next_to_corpus_words() -> None:
    traps = {r["id"]: r for r in load_dev6() if "trap" in r}
    assert len(traps) == 9
    labels = Counter(r["expect_decision"] for r in traps.values())
    assert labels == {"REFUSE_UNGROUNDED": 7, "REFUSE_NO_EVIDENCE": 2}
    assert traps["d6-36"]["query"] == "What country is the checkout_retry feature flag from?"


def test_dev6_is_in_the_heldout_resource_audit_and_clean() -> None:
    rel = "data/eval/synonym_dev6.jsonl"
    assert rel in HAND_WRITTEN
    assert audit((rel,))[rel] == []
