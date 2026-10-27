"""The committed seed-free calibration run follows the registered rule."""

import json
from pathlib import Path

from ops_copilot.passage_null_pool import GRID_Q, is_safe_setting, select

ROOT = Path(__file__).resolve().parents[1]
CAL = json.loads((ROOT / "artifacts" / "passage_null_pool_calibration.json").read_text())


def test_grid_rows_and_baseline():
    assert [r["null_min"] for r in CAL["results"]] == list(GRID_Q)
    assert CAL["n_rows"] == 171 and CAL["n_traps"] == 56
    b = CAL["baseline_shipped"]
    assert (b["correct"], b["answer_correct"], b["traps_opened"]) == (88, 24, [])


def test_safe_flags_and_choice_follow_the_registered_rule():
    for r in CAL["results"]:
        assert r["safe"] == is_safe_setting(r)
    assert [r["null_min"] for r in CAL["results"] if r["safe"]] == [0.38, 0.40]
    ch = select(CAL["results"])
    assert ch == CAL["chosen"] and ch["null_min"] == 0.40
    assert (ch["calib_correct"], ch["calib_answer_correct"], ch["rows_lost"], ch["answer_lost"]) == (83, 22, 5, 2)
    assert ch["new_errors"] == ["d2-17", "d2-24", "d3-02", "d3-28", "d4-27"] and ch["fixed"] == []


def test_at22_is_the_trap_that_sets_the_cut_and_no_v2_tune_trap_opens():
    by_q = {r["null_min"]: r for r in CAL["results"]}
    assert by_q[0.36]["traps_opened"] == ["at-22"] and not by_q[0.38]["traps_opened"]
    assert not any(t.startswith("at2-") for r in CAL["results"] for t in r["traps_opened"])
    assert not any(r["must_refuse_opened"] for r in CAL["results"])
    assert by_q[0.42]["rows_lost"] == 7  # over the 6-row cap
