"""The committed citation-aware calibration re-score agrees with the frozen protocol."""

import json
from pathlib import Path

from ops_copilot import nonkey_citation_protocol as P

ART = Path(__file__).resolve().parents[1] / "artifacts"


def _cal():
    return json.loads((ART / "nonkey_citation_calibration.json").read_text(encoding="utf-8"))


def test_rescore_reproduces_the_nov10_decision_counts():
    cal = _cal()
    arms = cal["arms"]
    nov10 = json.loads((ART / "nonkey_parts_calibration.json").read_text(encoding="utf-8"))["arms"]
    assert (cal["rows"], cal["swaps"]) == (320, 384)
    for n in P.ARMS:
        assert (arms[n]["passed"], arms[n]["answered"], arms[n]["refuse_opened"]) == (
            nov10[n]["passed"], nov10[n]["answered"], nov10[n]["refuse_opened"])


def test_d6_06_is_fixed_not_lost_and_no_arm_adds_wrong_evidence():
    cites = _cal()["citation"]
    for arm in ("all_hyphen", "all_joined", "corpus_hyphen"):
        c = cites[arm]
        assert c["decision_lost"] == ["d5-22", "d6-06", "d8-30"]
        assert (c["lost"], c["fixed"], c["unknown_lost"]) == (["d5-22"], ["d6-06"], ["d8-30"])
        assert c["budget_lost"] == 2 and c["new_wrong"] == []
    assert cites["all"]["budget_lost"] == 4


def test_pick_is_the_pre_stated_arm():
    cal = _cal()
    assert P.pick(cal["arms"], cal["citation"]) == cal["picked"] == P.EXPECTED_PICK == "all_hyphen"
