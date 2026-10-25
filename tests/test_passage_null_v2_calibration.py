"""The committed v2 (sticky veto) calibration artifact: pinned numbers quoted in the README."""

import json
from pathlib import Path

from ops_copilot.attribute_traps import half as trap_half
from ops_copilot.passage_null_dev5 import grid_settings_v2, selection_key
from ops_copilot.synonym_dev5 import half

ART = Path(__file__).resolve().parents[1] / "artifacts" / "passage_null_v2_calibration.json"


def _rep():
    return json.loads(ART.read_text())


def test_v2_covers_its_grid_and_no_confirm_row():
    rep = _rep()
    assert rep["n_settings"] == len(grid_settings_v2()) == 5
    assert all(r["sticky"] for r in rep["results"])
    confirm = {r["id"] for r in half("confirm")} | {r["id"] for r in trap_half("confirm")}
    for r in rep["results"]:
        assert not confirm & (set(r["fixed"]) | set(r["new_errors"]) | set(r["traps_opened"]))


def test_v2_chooses_q030_the_only_safe_setting():
    rep = _rep()
    by_q = {r["null_min"]: r for r in rep["results"]}
    assert [by_q[q]["safe"] for q in (0.1, 0.2, 0.3, 0.4, 0.5)] == [False, False, True, False, False]
    assert [len(by_q[q]["traps_opened"]) for q in (0.1, 0.2, 0.3, 0.4, 0.5)] == [4, 2, 0, 0, 0]
    c = rep["chosen"]
    assert rep["candidate"] is True and c["null_min"] == 0.3 and c == sorted(rep["results"], key=selection_key)[0]
    assert (c["calib_correct"], c["calib_answer_correct"]) == (88, 24)
    assert c["new_errors"] == ["d3-09", "d3-27", "d4-29", "d4-42", "d5-02"] and c["n_answer_lost"] == 2
    assert c["fixed"] == ["d5-38"] and c["must_refuse_opened"] == [] and c["sweep_labelled_trap_opened"] == []
