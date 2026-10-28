"""dev7: fresh paraphrases, guarded vocabulary, frozen source-grouped split."""

from collections import Counter

from ops_copilot.resource_audit import audit
from ops_copilot.synonym_dev5 import group_key
from ops_copilot.synonym_dev6 import load_dev6
from ops_copilot.synonym_dev7 import half, load_dev7, must_refuse_rows, split_dev7, summary, vocabulary_problems

CONFIRM_IDS = ["d7-10", "d7-11", "d7-14", "d7-15", "d7-16", "d7-17", "d7-18", "d7-19", "d7-20",
               "d7-21", "d7-22", "d7-23", "d7-26", "d7-27", "d7-30", "d7-33", "d7-38", "d7-39"]


def test_shape_and_labels():
    rows = load_dev7()
    assert len(rows) == 40 and len({r["id"] for r in rows}) == 40 and len({r["query"] for r in rows}) == 40
    assert Counter(r["expect_decision"] for r in rows) == {
        "ANSWER": 26, "REFUSE_STALE": 4, "REFUSE_UNGROUNDED": 7, "REFUSE_CANARY": 1,
        "REFUSE_PII": 1, "PROPOSE_WRITE": 1}
    assert len(must_refuse_rows(rows)) == 13
    assert sum("trap" in r for r in rows) == 3


def test_vocabulary_guard_is_clean_and_no_heldout_word():
    assert vocabulary_problems() == {}
    rel = "data/eval/synonym_dev7.jsonl"
    assert audit((rel,)) == {rel: []}


def test_no_query_repeats_dev6():
    assert not {r["query"] for r in load_dev7()} & {r["query"] for r in load_dev6()}


def test_split_groups_whole_sources_and_is_frozen():
    rows = load_dev7()
    sp = split_dev7(rows)
    by_group = {}
    for r in rows:
        by_group.setdefault(group_key(r), set()).add(sp[r["id"]])
    assert all(len(v) == 1 for v in by_group.values())
    assert [r["id"] for r in half("confirm")] == CONFIRM_IDS
    assert len(half("tune")) == 22
    assert summary()["confirm"] == {"ANSWER": 13, "REFUSE_STALE": 2, "REFUSE_UNGROUNDED": 3}
