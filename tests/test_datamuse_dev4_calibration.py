"""The committed dev4 calibration artifact agrees with the pre-registered protocol."""

import json
from pathlib import Path

from ops_copilot.datamuse_dev4 import grid_settings, selection_key
from ops_copilot.synonym_dev4 import half

ART = Path(__file__).resolve().parents[1] / "artifacts" / "datamuse_dev4_calibration.json"
KNOBS = ("max_rank", "max_neighbours", "context_min")


def _rep():
    return json.loads(ART.read_text())


def test_artifact_covers_the_whole_grid_and_no_confirm_row():
    rep = _rep()
    assert rep["n_settings"] == len(grid_settings()) == 24
    assert rep["rows_by_set"] == {"dev": 15, "dev2": 43, "dev3": 45, "dev4_tune": 23}
    confirm = {r["id"] for r in half("confirm")}
    for r in rep["results"]:
        assert not confirm & set(r["fixed"]) and not confirm & set(r["new_errors"])
        assert not confirm & set(r["must_refuse_opened"])


def test_chosen_is_the_minimum_of_the_selection_key_and_passes_every_safety_check():
    rep = _rep()
    best = min(rep["results"], key=selection_key)
    assert {k: best[k] for k in KNOBS} == {k: rep["chosen"][k] for k in KNOBS}
    c = rep["chosen"]
    assert c["safe"] and c["clean_accuracy"] == 1.0 and not c["new_errors"]
    assert not c["must_refuse_opened"] and not c["sweep_labelled_trap_opened"]
    assert rep["candidate"] is (c["calib_correct"] > rep["baseline_off"]["correct"])
    assert {k: c[k] for k in KNOBS} == {"max_rank": 100, "max_neighbours": 2, "context_min": 2}
    assert (c["calib_correct"], rep["baseline_off"]["correct"], rep["n_safe"]) == (84, 75, 13)


def test_the_must_refuse_check_rejects_the_higher_scoring_context_1_arms():
    rep = _rep()
    top = max(rep["results"], key=lambda r: r["calib_correct"])
    assert top["calib_correct"] == 86 and not top["safe"]
    assert "d3-33" in top["must_refuse_opened"]
