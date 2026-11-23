"""The committed duplicate-paraphrase calibration record agrees with the frozen protocol."""

import json
from pathlib import Path

from ops_copilot import dupe_paraphrase_protocol as P

ART = Path(__file__).resolve().parents[1] / "artifacts"


def _cal():
    return json.loads((ART / "dupe_paraphrase_calibration.json").read_text(encoding="utf-8"))


def test_calibration_numbers():
    cal = _cal()
    arms = cal["arms"]
    assert (cal["rows"], cal["swaps"]) == (320, 384)
    assert {n: a["passed"] for n, a in arms.items()} == {
        "shipped": 14, "strict_known": 18, "strict_lone": 18, "strict_all": 18, "loose_lone": 21, "loose_all": 24}
    assert {n: P.gain(a, arms["shipped"]) for n, a in arms.items()} == {
        "shipped": 0, "strict_known": 0, "strict_lone": 1, "strict_all": 1, "loose_lone": 3, "loose_all": 2}
    assert arms["shipped"]["answered"] == 52 and arms["shipped"]["n_answer_rows"] == 165
    assert {n: a["refuse_opened"] for n, a in arms.items()} == {n: 5 for n in P.ARMS}
    assert {n: len(c["new_wrong"]) for n, c in cal["citation"].items()} == {n: 0 for n in P.ARMS if n != "shipped"}


def test_every_arm_breaks_the_swap_budget():
    arms = _cal()["arms"]
    for n in P.ARMS:
        if n != "shipped":
            assert P.swap_rise(arms[n], arms["shipped"]) > P.MAX_SWAP_RISE
    # the strict arms miss it by one swap: 4 of 384 = 0.0104
    assert arms["strict_known"]["passed"] - arms["shipped"]["passed"] == 4


def test_nothing_is_picked_so_the_confirm_and_dev10_stay_unspent():
    cal = _cal()
    wrong = {n: len(c["new_wrong"]) for n, c in cal["citation"].items()}
    assert P.pick(cal["arms"], wrong) is None and cal["picked"] is None
    assert not (ART / "dupe_paraphrase_confirm.json").exists()


def test_gained_rows_and_the_one_lost_answer():
    changed = _cal()["changed_rows"]
    gained = {n: sorted(r["id"] for r in rows if r["arm"] == "ANSWER") for n, rows in changed.items()}
    assert gained == {"strict_known": [], "strict_lone": ["d6-23"], "strict_all": ["d6-23"],
                      "loose_lone": ["d3-21", "d6-23", "d8-32"], "loose_all": ["d3-21", "d6-23", "d8-32"]}
    lost = {r["id"]: r["arm"] for r in changed["loose_all"] if r["shipped"] == "ANSWER"}
    assert lost == {"d8-03": "REFUSE_DISAGREE"}
    assert _cal()["citation"]["loose_all"]["decision_lost"] == ["d8-03"]
