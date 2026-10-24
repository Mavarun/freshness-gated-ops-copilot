"""The committed dev5 calibration artifact agrees with the pre-registered protocol."""

import json
from pathlib import Path

from ops_copilot.datamuse_dev5 import grid_settings, selection_key
from ops_copilot.synonym_dev5 import half

ART = Path(__file__).resolve().parents[1] / "artifacts" / "datamuse_dev5_calibration.json"
KNOBS = ("max_rank", "max_neighbours", "context_min", "sense_min")


def _rep():
    return json.loads(ART.read_text())


def test_artifact_covers_the_whole_grid_and_no_confirm_row():
    rep = _rep()
    assert rep["n_settings"] == len(grid_settings()) == 48
    assert rep["rows_by_set"] == {"dev": 15, "dev2": 43, "dev3": 45, "dev4": 44, "dev5_tune": 24}
    confirm = {r["id"] for r in half("confirm")}
    for r in rep["results"]:
        assert not confirm & set(r["fixed"]) and not confirm & set(r["new_errors"])
        assert not confirm & set(r["must_refuse_opened"])


def test_no_setting_is_safe_because_the_shipped_default_already_answers_d5_38():
    rep = _rep()
    assert rep["n_safe"] == 0 and rep["candidate"] is False
    assert rep["baseline_off_opened_must_refuse"] == ["d5-38"]
    assert rep["baseline_off"]["n_fail_open"] == 1
    assert all(r["n_fail_open"] >= 1 for r in rep["results"])
    clean_but_inherited = [
        r for r in rep["results"]
        if not r["new_errors"] and not r["must_refuse_opened"] and not r["sweep_labelled_trap_opened"]
        and r["n_fail_open"] == 1 and r["clean_accuracy"] == 1.0
    ]
    assert len(clean_but_inherited) == 42


def test_chosen_is_the_minimum_of_the_selection_key_and_records_the_would_be_gain():
    rep = _rep()
    best = min(rep["results"], key=selection_key)
    assert {k: best[k] for k in KNOBS} == {k: rep["chosen"][k] for k in KNOBS}
    c = rep["chosen"]
    assert {k: c[k] for k in KNOBS} == {"max_rank": 100, "max_neighbours": 1, "context_min": 2, "sense_min": 0.3}
    assert (c["calib_correct"], rep["baseline_off"]["correct"]) == (101, 92)
    assert (c["calib_answer_correct"], rep["baseline_off"]["answer_correct"]) == (34, 26)
    assert not c["new_errors"] and not c["must_refuse_opened"] and c["sweep_n_opened"] == 0


def test_the_sense_gate_keeps_the_pr27_trap_closed_in_every_arm():
    rep = _rep()
    assert not any("d4-37" in r["must_refuse_opened"] for r in rep["results"])
    # rank 100 without the context gate still opens the restart trap d3-33
    assert sum("d3-33" in r["must_refuse_opened"] for r in rep["results"]) == 6
