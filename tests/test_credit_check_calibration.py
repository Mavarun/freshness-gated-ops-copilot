"""The committed credited-word calibration: chosen arm, cost and safety pinned to the artifact."""

import json
from pathlib import Path

from ops_copilot.credit_check import MAX_ANSWER_LOST, MAX_ROWS_LOST, grid_settings, is_safe_setting, selection_key

ART = json.loads((Path(__file__).resolve().parents[1] / "artifacts" / "credit_check_calibration.json").read_text())


def test_covers_the_whole_grid_on_the_registered_rows():
    assert ART["n_settings"] == len(grid_settings()) == 31
    assert ART["n_rows"] == 238 and ART["n_traps"] == 95
    assert ART["rows_by_set"] == {"dev": 15, "dev2": 43, "dev3": 45, "dev4": 44, "dev5_tune": 24,
                                  "dev6": 45, "dev7_tune": 22}


def test_baseline_opens_only_the_known_trap():
    b = ART["baseline_shipped"]
    assert (b["correct"], b["answer_correct"]) == (114, 28)
    assert b["traps_opened"] == ["at2-01"] and b["opened_must_refuse"] == []


def test_chosen_is_stop_words_only_at_a_cost_of_four_rows():
    ch = ART["chosen"]
    assert (ch["stop"], ch["top_freq"], ch["max_rank"]) == (True, 0, 0)
    assert (ch["calib_correct"], ch["calib_answer_correct"]) == (110, 25)
    assert ch["new_errors"] == ["d3-02", "d4-43", "d5-18", "d6-09"] and ch["fixed"] == []
    assert ch["rows_lost"] == 4 <= MAX_ROWS_LOST and ch["answer_lost"] == 3 <= MAX_ANSWER_LOST
    assert ch["traps_opened"] == [] and ch["must_refuse_opened"] == []


def test_only_two_arms_are_safe_and_the_rule_is_reapplied_exactly():
    safe = [(r["stop"], r["top_freq"], r["max_rank"]) for r in ART["results"] if r["safe"]]
    assert safe == [(True, 0, 0), (True, 0, 2000)]
    assert all(r["safe"] == is_safe_setting(r) for r in ART["results"])
    assert ART["results"] == sorted(ART["results"], key=selection_key)


def test_rank_alone_cannot_close_at2_01_and_frequency_lists_cost_too_much():
    by = {(r["stop"], r["top_freq"], r["max_rank"]): r for r in ART["results"]}
    assert by[(False, 0, 2000)]["traps_opened"] == ["at2-01"]
    assert by[(False, 0, 1000)]["traps_opened"] == ["at2-01"]
    assert all(by[(False, f, 0)]["rows_lost"] > MAX_ROWS_LOST for f in (50, 100, 200))
