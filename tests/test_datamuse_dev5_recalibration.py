"""dev5 Datamuse grid re-run on top of the 2026-10-25 default (null-control test on)."""

import json
from pathlib import Path

from ops_copilot.attribute_traps import load_traps, score_traps
from ops_copilot.datamuse_dev5 import config_for, selection_key

ART = Path(__file__).resolve().parents[1] / "artifacts" / "datamuse_dev5_recalibration.json"
KNOBS = ("max_rank", "max_neighbours", "context_min", "sense_min")


def _rep():
    return json.loads(ART.read_text())


def test_with_d5_38_closed_the_grid_has_safe_arms_and_a_candidate():
    rep = _rep()
    b, c = rep["baseline_off"], rep["chosen"]
    assert rep["baseline_off_opened_must_refuse"] == []
    assert (rep["n_safe"], rep["n_settings"]) == (42, 48) and rep["candidate"] is True
    assert (b["correct"], b["answer_correct"]) == (88, 24)
    assert {k: c[k] for k in KNOBS} == {"max_rank": 100, "max_neighbours": 1, "context_min": 2, "sense_min": 0.30}
    assert (c["calib_correct"], c["calib_answer_correct"]) == (98, 33)
    assert c["new_errors"] == [] and c["must_refuse_opened"] == [] and c["sweep_labelled_trap_opened"] == []
    assert c == sorted(rep["results"], key=selection_key)[0]


def test_candidate_refuses_every_attribute_trap():
    c = _rep()["chosen"]
    assert score_traps(config_for({k: c[k] for k in KNOBS}), load_traps())["opened"] == []
