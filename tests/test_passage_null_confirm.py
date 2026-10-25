"""The committed one-shot confirm of the v2-chosen null-control test."""

import json
from pathlib import Path

ART = Path(__file__).resolve().parents[1] / "artifacts" / "passage_null_confirm.json"


def test_confirm_record():
    rep = json.loads(ART.read_text())
    assert rep["chosen"] == {"null_min": 0.3, "sticky": True}
    assert rep["decision"]["default_on"] is True and all(rep["decision"]["checks"].values())
    c = rep["dev5_confirm"]
    assert (c["off"]["correct"], c["on"]["correct"], c["off"]["n"]) == (8, 7, 20)
    assert (c["off"]["answer_correct"], c["on"]["answer_correct"]) == (3, 2)
    assert c["new_errors"] == ["d5-13"] and c["fixed"] == []
    assert c["must_refuse_opened_off"] == [] and c["must_refuse_opened_on"] == []
    t = rep["traps_confirm"]
    assert t["off"]["opened"] == ["at-01", "at-21"] and t["on"]["opened"] == [] and t["on"]["n"] == 18
    r = rep["robustness"]
    assert r["changed_vs_off"] == []
    for k in ("off", "on"):
        h = r[k]["per_synonym_split"]["heldout"]
        assert r[k]["clean_accuracy"] == 1.0 and r[k]["n_fail_open"] == 0
        assert round(h["perturbed_accuracy"], 3) == 0.514 and h["by_gate"]["ANSWER"] == {"n": 9, "correct": 0}
