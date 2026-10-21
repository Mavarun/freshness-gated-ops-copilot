"""The committed one-shot dev3 confirm artifact: rule applied as pre-registered."""

import json
from pathlib import Path

from ops_copilot.synonym_dev3 import half

ART = Path(__file__).resolve().parents[1] / "artifacts"


def _c():
    return json.loads((ART / "datamuse_dev3_confirm.json").read_text())


def test_confirm_uses_the_calibration_choice_and_only_confirm_rows():
    c = _c()
    cal = json.loads((ART / "datamuse_dev3_calibration.json").read_text())
    assert c["chosen"] == {k: cal["chosen"][k] for k in ("scope", "max_rank", "max_neighbours", "context_min")}
    ids = {r["id"] for r in half("confirm")}
    assert set(c["confirm"]["off"]["decisions"]) == ids == set(c["confirm"]["on"]["decisions"])
    assert c["confirm"]["off"]["n"] == 20


def test_decision_is_the_conjunction_of_the_pre_registered_checks():
    d = _c()["decision"]
    assert set(d["checks"]) == {
        "confirm_gain", "confirm_answer_not_down", "confirm_no_new_error", "confirm_no_fail_open_write_pii",
        "clean_1", "robustness_no_fail_open_write_pii", "heldout_acc_not_down", "heldout_answer_not_down",
    }
    assert d["default_on"] is all(d["checks"].values())


def test_recorded_numbers():
    c = _c()
    off, on = c["confirm"]["off"], c["confirm"]["on"]
    assert (off["correct"], on["correct"], off["answer_correct"], on["answer_correct"]) == (11, 14, 4, 7)
    assert c["confirm"]["new_errors"] == [] and c["decision"]["default_on"] is True
    ho = c["robustness"]["on"]["per_synonym_split"]["heldout"]
    assert ho["by_gate"]["ANSWER"]["correct"] == 1 and abs(ho["perturbed_accuracy"] - 0.6) < 1e-9
    assert c["robustness"]["on"]["clean_accuracy"] == 1.0
    # reference arms are recorded, not used by the decision
    assert set(c["reference_arms"]) == {"wordnet_dev2_chosen", "datamuse_dev2_chosen"}
