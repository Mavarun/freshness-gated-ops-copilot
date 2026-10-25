"""The committed null-control calibration artifact agrees with the pre-registered protocol."""

import json
from pathlib import Path

from ops_copilot.attribute_traps import half as trap_half
from ops_copilot.passage_null_dev5 import grid_settings, selection_key
from ops_copilot.synonym_dev5 import half

ART = Path(__file__).resolve().parents[1] / "artifacts" / "passage_null_calibration.json"


def _rep():
    return json.loads(ART.read_text())


def test_artifact_covers_the_grid_and_no_confirm_row():
    rep = _rep()
    assert rep["n_settings"] == len(grid_settings()) == 5
    assert (rep["n_rows"], rep["n_trap_rows"]) == (171, 18)
    confirm = {r["id"] for r in half("confirm")} | {r["id"] for r in trap_half("confirm")}
    for r in rep["results"]:
        touched = set(r["fixed"]) | set(r["new_errors"]) | set(r["must_refuse_opened"]) | set(r["traps_opened"])
        assert not confirm & touched


def test_baseline_is_the_shipped_default_with_d5_38_and_five_tune_traps_open():
    b = _rep()["baseline_off"]
    assert (b["correct"], b["answer_correct"]) == (92, 26)
    assert b["opened_must_refuse"] == ["d5-38"]
    assert b["traps_opened"] == ["at-07", "at-12", "at-22", "at-25", "at-33"]


def test_every_q_closes_d5_38_but_none_is_safe_so_the_test_ships_off():
    rep = _rep()
    by_q = {r["null_min"]: r for r in rep["results"]}
    assert all(r["fixed"] == ["d5-38"] and r["must_refuse_opened"] == [] for r in by_q.values())
    assert [len(by_q[q]["traps_opened"]) for q in (0.1, 0.2, 0.3, 0.4, 0.5)] == [4, 3, 2, 2, 2]
    assert [by_q[q]["calib_correct"] for q in (0.1, 0.2, 0.3, 0.4, 0.5)] == [93, 92, 91, 89, 89]
    assert by_q[0.1]["new_errors"] == []
    assert by_q[0.5]["traps_opened"] == ["at-22", "at-25"]
    assert rep["n_safe"] == 0 and rep["candidate"] is False


def test_chosen_follows_the_selection_key():
    rep = _rep()
    assert rep["chosen"] == sorted(rep["results"], key=selection_key)[0]
