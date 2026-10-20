"""Post-hoc Datamuse coverage buckets (synthetic table + committed artifact)."""

import json
from pathlib import Path

from ops_copilot.datamuse_coverage import bucket_row, coverage, link_rank
from ops_copilot.datamuse_senses import DatamuseSense, DatamuseTable

TABLE = DatamuseTable(
    meta={"corpus_words": ["latency", "rotation", "size", "status"]},
    neighbours={
        "delay": (("latency", 4, True, "rev"),),
        "turnover": (("size", 2, True, "rev"), ("rotation", 57, True, "rev")),
        "standing": (),
    },
)


def _b():
    return DatamuseSense(table=TABLE, max_rank=10, max_neighbours=1, lone_unknown=True)


def _row(rid, swap, want="ANSWER"):
    return {"id": rid, "swap": swap, "expect_decision": want}


def test_link_rank_is_ungated():
    assert link_rank(_b(), "turnover", "rotation") == 57
    assert link_rank(_b(), "standing", "status") is None


def test_buckets():
    b = _b()
    assert bucket_row(_row("a", "status -> standing"), "REFUSE_UNGROUNDED", "REFUSE_UNGROUNDED", b)["bucket"] == "no_link"
    assert bucket_row(_row("b", "rotation -> turnover"), "REFUSE_UNGROUNDED", "REFUSE_UNGROUNDED", b)["bucket"] == "outside_gate"
    assert bucket_row(_row("c", "latency -> delay"), "REFUSE_STALE", "REFUSE_UNGROUNDED", b)["bucket"] == "mapped_still_wrong"
    ok = bucket_row(_row("d", "latency -> delay"), "ANSWER", "REFUSE_UNGROUNDED", b)
    assert ok["bucket"] == "correct" and ok["right_without_link"] is False


def test_fixed_through_a_different_word_is_flagged():
    got = bucket_row(_row("e", "rotation -> turnover"), "ANSWER", "REFUSE_UNGROUNDED", _b())
    assert got["bucket"] == "correct" and got["right_without_link"] is True
    assert got["gate_maps_to"] == ["size"]
    # already right with the flag off: not counted as a fix
    assert bucket_row(_row("f", "rotation -> turnover"), "ANSWER", "ANSWER", _b())["right_without_link"] is False


def test_coverage_counts_and_suspend_flag_is_restored():
    b = _b()
    b.set_suspend_unknown(True)
    rows = [_row("a", "status -> standing"), _row("e", "rotation -> turnover")]
    cov = coverage(rows, {"a": "REFUSE_UNGROUNDED", "e": "ANSWER"}, {"a": "REFUSE_UNGROUNDED", "e": "REFUSE_UNGROUNDED"}, b)
    assert cov["counts"]["no_link"] == 1 and cov["counts"]["correct"] == 1
    assert cov["n_right_without_link"] == 1
    assert cov["n_linked_rank_le"] == {10: 0, 20: 0, 50: 0, 100: 1}
    assert b.suspend_unknown is True


def test_committed_artifact_matches_the_readme_numbers():
    art = json.loads((Path(__file__).resolve().parents[1] / "artifacts" / "datamuse_coverage.json").read_text())
    w = art["dev2"]["wordnet_no_link"]
    assert (w["n"], w["datamuse_rank_le_10"], w["datamuse_rank_le_100"], w["correct_under_arm"]) == (7, 1, 4, 2)
    assert art["dev2"]["n_right_without_link"] == 2
    assert art["dev2"]["rows"]["d2-18"]["gate_maps_to"] == ["size"]
