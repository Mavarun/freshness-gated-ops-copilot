"""The committed calibration record agrees with the frozen protocol's pick rule."""

import json
from pathlib import Path

from ops_copilot import nonkey_coverage_protocol as P

ART = Path(__file__).resolve().parents[1] / "artifacts"


def _cal():
    return json.loads((ART / "nonkey_calibration.json").read_text(encoding="utf-8"))


def test_calibration_numbers():
    cal = _cal()
    arms = cal["arms"]
    assert (cal["rows"], cal["swaps"]) == (272, 384)
    assert {n: a["passed"] for n, a in arms.items()} == {
        "shipped": 42, "all": 14, "corpus": 14, "idf_q25": 34, "idf_q50": 42, "cov_065": 38}
    assert arms["shipped"]["by_mechanism"]["unsupported"] == 25
    assert arms["all"]["by_mechanism"]["unsupported"] == 0
    assert {n: P.lost(a, arms["shipped"]) for n, a in arms.items()}["all"] == 2


def test_pick_reproduces_from_the_record():
    cal = _cal()
    assert P.pick(cal["arms"]) == cal["picked"] == "all"  # ties 'corpus' on rate and rows; earlier arm
    assert [r["id"] for r in cal["lost_rows"]["all"]] == ["d5-22", "d6-06"]
