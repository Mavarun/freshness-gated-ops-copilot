"""The committed dev3 calibration artifact agrees with the pre-registered protocol."""

import json
from pathlib import Path

from ops_copilot.datamuse_dev3 import grid_settings, selection_key
from ops_copilot.synonym_dev3 import half

ART = Path(__file__).resolve().parents[1] / "artifacts" / "datamuse_dev3_calibration.json"


def _rep():
    return json.loads(ART.read_text())


def test_artifact_covers_the_whole_grid_and_no_confirm_row():
    rep = _rep()
    assert rep["n_settings"] == len(grid_settings())
    assert rep["rows_by_set"] == {"dev": 15, "dev2": 43, "dev3_calib": 25}
    confirm = {r["id"] for r in half("confirm")}
    assert not confirm & set(rep["baseline_off"]["decisions"])
    for r in rep["results"]:
        assert not confirm & set(r["fixed"]) and not confirm & set(r["new_errors"])


def test_chosen_is_the_minimum_of_the_selection_key_and_is_safe():
    rep = _rep()
    best = min(rep["results"], key=selection_key)
    assert {k: best[k] for k in ("scope", "max_rank", "max_neighbours", "context_min")} == {
        k: rep["chosen"][k] for k in ("scope", "max_rank", "max_neighbours", "context_min")
    }
    c = rep["chosen"]
    assert c["safe"] and c["clean_accuracy"] == 1.0 and not c["new_errors"]
    assert rep["candidate"] is (c["calib_correct"] > rep["baseline_off"]["correct"])


def test_shelved_dev2_arm_is_unsafe_on_the_wider_calibration_rows():
    rep = _rep()
    dev2_arm = next(r for r in rep["results"] if (r["scope"], r["max_rank"], r["max_neighbours"],
                                                  r["context_min"]) == ("lone", 10, 2, 0))
    assert not dev2_arm["safe"] and "d2-17" in dev2_arm["new_errors"]
