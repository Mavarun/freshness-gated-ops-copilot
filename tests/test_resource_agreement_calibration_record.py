"""The committed resource-agreement calibration record agrees with the frozen protocol."""

import json
from pathlib import Path

from ops_copilot import resource_agreement_protocol as P

ART = Path(__file__).resolve().parents[1] / "artifacts"


def _cal():
    return json.loads((ART / "resource_agreement_calibration.json").read_text(encoding="utf-8"))


def test_calibration_numbers():
    cal = _cal()
    arms = cal["arms"]
    assert (cal["rows"], cal["swaps"]) == (320, 384)
    assert {n: a["passed"] for n, a in arms.items()} == {
        "shipped": 42, "agree2_known": 45, "agree3_known": 43, "agree2_lone": 55, "agree2_all": 58, "agree3_all": 49}
    assert {n: P.gain(a, arms["shipped"]) for n, a in arms.items()} == {
        "shipped": 0, "agree2_known": 0, "agree3_known": 0, "agree2_lone": 6, "agree2_all": 3, "agree3_all": 4}
    assert {n: a["refuse_opened"] for n, a in arms.items()} == {n: 8 for n in P.ARMS}
    assert {n: len(c["new_wrong"]) for n, c in cal["citation"].items()} == {
        "agree2_known": 0, "agree3_known": 0, "agree2_lone": 1, "agree2_all": 0, "agree3_all": 0}


def test_every_gaining_arm_breaks_the_swap_budget():
    arms = _cal()["arms"]
    for n in ("agree2_lone", "agree2_all", "agree3_all"):
        assert P.swap_rise(arms[n], arms["shipped"]) > P.MAX_SWAP_RISE
    for n in ("agree2_known", "agree3_known"):
        assert P.gain(arms[n], arms["shipped"]) < P.MIN_GAIN_CAL


def test_nothing_is_picked_so_the_confirm_and_dev10_stay_unspent():
    cal = _cal()
    wrong = {n: len(c["new_wrong"]) for n, c in cal["citation"].items()}
    assert P.pick(cal["arms"], wrong) is None and cal["picked"] is None
    assert not (ART / "resource_agreement_confirm.json").exists()


def test_all_scope_two_votes_also_loses_right_evidence_answers_to_disagreement():
    c = _cal()["citation"]["agree2_all"]
    assert c["lost"] == ["golden-25", "d2-16", "d4-21", "d5-21"] and c["unknown_lost"] == ["d8-01"]
    changed = {r["id"]: r["arm"] for r in _cal()["changed_rows"]["agree2_all"]}
    assert all(changed[i] == "REFUSE_DISAGREE" for i in ("golden-25", "d2-16", "d4-21", "d5-21", "d8-01"))
