"""The committed compound-parts calibration record agrees with the frozen protocol."""

import json
from pathlib import Path

from ops_copilot import nonkey_parts_protocol as P

ART = Path(__file__).resolve().parents[1] / "artifacts"


def _cal():
    return json.loads((ART / "nonkey_parts_calibration.json").read_text(encoding="utf-8"))


def test_calibration_numbers():
    cal = _cal()
    arms = cal["arms"]
    assert (cal["rows"], cal["swaps"]) == (320, 384)
    assert {n: a["passed"] for n, a in arms.items()} == {
        "shipped": 42, "all": 14, "all_hyphen": 14, "all_joined": 14, "corpus_hyphen": 14}
    assert {n: P.lost(a, arms["shipped"]) for n, a in arms.items()} == {
        "shipped": 0, "all": 5, "all_hyphen": 3, "all_joined": 3, "corpus_hyphen": 3}
    assert {n: a["refuse_opened"] for n, a in arms.items()} == {
        "shipped": 8, "all": 5, "all_hyphen": 5, "all_joined": 5, "corpus_hyphen": 5}


def test_parts_win_back_exactly_the_two_hyphen_rows():
    lost = {n: [r["id"] for r in v] for n, v in _cal()["lost_rows"].items()}
    assert lost["all"] == ["d5-22", "d6-06", "d8-06", "d8-29", "d8-30"]
    for arm in ("all_hyphen", "all_joined", "corpus_hyphen"):
        assert lost[arm] == ["d5-22", "d6-06", "d8-30"]


def test_nothing_is_picked_so_the_confirm_and_dev9_stay_unspent():
    cal = _cal()
    assert P.pick(cal["arms"]) is None and cal["picked"] is None
    assert not (ART / "nonkey_parts_confirm.json").exists()
