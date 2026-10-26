"""Recorded seed-sensitivity result: the shipped 0-of-36 trap result is specific to seed 42."""

import json
from collections import Counter
from pathlib import Path

from ops_copilot.attribute_traps import split_traps
from ops_copilot.config import CopilotConfig

ART = Path(__file__).resolve().parents[1] / "artifacts"


def _out() -> dict:
    return json.loads((ART / "passage_null_seeds.json").read_text())


def test_reference_seed_reproduces_the_shipped_numbers():
    for block in _out().values():
        ref = block["reference"]
        assert (ref["calib_correct"], ref["calib_answer_correct"]) == (88, 24)
        assert ref["traps_opened"] == [] and ref["must_refuse_opened"] == [] and ref["clean_accuracy"] == 1.0


def test_primary_is_not_seed_stable_traps_reopen_but_calibration_and_must_refuse_hold():
    p = _out()["primary"]
    assert p["verdict"]["stable"] is False
    assert p["n_safe_seeds"] == 1 and p["verdict"]["drift_seeds"] == []
    assert (p["calib_correct_min"], p["calib_correct_max"]) == (85, 89)
    assert all(not s["must_refuse_opened"] and s["clean_accuracy"] == 1.0 for s in p["seeds"].values())
    opened = Counter(t for s in p["seeds"].values() for t in s["traps_opened"])
    assert opened == {"at-22": 17, "at-12": 10, "at-33": 2, "at-01": 1, "at-21": 1}
    halves = split_traps()
    assert sum(n for t, n in opened.items() if halves[t] == "confirm") == 2  # both from one seed (8)


def test_300_controls_do_not_fix_it():
    s = _out()["secondary_300_controls"]
    assert s["verdict"]["stable"] is False and s["n_safe_seeds"] == 1
    opened = Counter(t for x in s["seeds"].values() for t in x["traps_opened"])
    assert opened["at-22"] == 19


def test_report_only_the_shipped_seed_is_unchanged():
    cfg = CopilotConfig()
    assert (cfg.passage_support_null_seed, cfg.passage_support_null_controls) == (42, 100)
    assert cfg.passage_support_null_min == 0.30 and cfg.passage_support_null_sticky
