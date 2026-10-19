"""Post-hoc coverage buckets (synthetic table) and the committed dev2 result."""

import json
from pathlib import Path

from ops_copilot.wordnet_coverage import BUCKETS, bucket_row, coverage, link, swap_pairs
from ops_copilot.wordnet_senses import WordNetNounSense, WordNetTable

TABLE = WordNetTable(
    meta={"corpus_words": ["gadget", "device", "widget"]},
    neighbours={
        "gizmo": (("gadget", "syn", 0, 0, 0),),
        "berry": (("device", "hypo", 1, 0, 1),),
        "trinket": (("widget", "syn", 0, 0, 3),),
    },
)


def b(**kw):
    return WordNetNounSense(max_path=1, max_neighbours=1, lone_unknown=True, table=TABLE, **kw)


def row(swap, want="ANSWER"):
    return {"id": "r", "query": "q", "expect_decision": want, "swap": swap}


def test_swap_pairs_single_words_only():
    assert swap_pairs(row("gadget -> gizmo")) == [("gadget", "gizmo")]
    assert swap_pairs(row("now -> at this moment")) == []
    assert swap_pairs({"id": "t", "trap": "x"}) == []


def test_link_uses_morphy_fallback_and_ignores_the_gate():
    assert link(b(), "berries", "device")["relation"] == "hypo"
    assert link(b(), "gizmo", "device") is None


def test_buckets():
    assert bucket_row(row("gadget -> gizmo"), "ANSWER", b())["bucket"] == "correct"
    assert bucket_row(row("gadget -> gizmo"), "REFUSE_UNGROUNDED", b())["bucket"] == "mapped_still_wrong"
    assert bucket_row(row("gadget -> thingy"), "REFUSE_UNGROUNDED", b())["bucket"] == "no_link"
    # Link exists via morphy + sense rank 1, but the gate (no morphy, first sense) drops it.
    got = bucket_row(row("device -> berries"), "REFUSE_UNGROUNDED", b(max_sense_rank=1))
    assert got["bucket"] == "outside_gate" and got["link"]["sense_rank"] == 1
    assert bucket_row(row("widget -> trinket"), "REFUSE_UNGROUNDED", b(max_sense_rank=1))["bucket"] == "outside_gate"
    assert bucket_row(row("now -> soon"), "REFUSE_UNGROUNDED", b())["bucket"] == "not_applicable"


def test_coverage_counts_every_bucket_and_skips_traps():
    rows = [row("gadget -> gizmo") | {"id": "a"}, {"id": "t", "query": "q", "expect_decision": "ANSWER", "trap": "x"}]
    out = coverage(rows, {"a": "ANSWER", "t": "ANSWER"}, b())
    assert set(out["counts"]) == set(BUCKETS) and out["counts"]["correct"] == 1
    assert set(out["rows"]) == {"a"}


def test_committed_dev2_coverage():
    out = json.loads((Path(__file__).resolve().parents[1] / "artifacts/wordnet_coverage.json").read_text())
    assert out["dev2"]["counts"] == {
        "no_link": 7, "outside_gate": 4, "mapped_still_wrong": 0, "correct": 23, "not_applicable": 1,
    }
    assert out["fresh"]["counts"]["no_link"] == 6
