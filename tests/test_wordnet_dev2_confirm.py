"""dev2 one-shot confirm: committed result and the ships-off decision."""

import json
from pathlib import Path

from ops_copilot.config import CopilotConfig
from ops_copilot.synonym_dev2 import half

ART = Path(__file__).resolve().parents[1] / "artifacts"


def _confirm():
    return json.loads((ART / "wordnet_dev2_confirm.json").read_text())


def test_confirm_ran_the_calibrated_choice_only():
    cal = json.loads((ART / "wordnet_dev2_calibration.json").read_text())["chosen"]
    out = _confirm()
    for k in ("scope", "max_path", "max_fanout", "max_neighbours", "morphy", "max_sense_rank"):
        assert out["chosen"][k] == cal[k]
    assert set(out["confirm"]["off"]["decisions"]) == {r["id"] for r in half("confirm")}


def test_confirm_found_no_gain_so_the_flag_ships_off():
    out = _confirm()
    d = out["decision"]
    assert d["default_on"] is False
    assert d["checks"]["confirm_gain"] is False
    # Every no-harm check passed: it is off for lack of gain, not for harm.
    assert all(v for k, v in d["checks"].items() if k != "confirm_gain")
    assert out["confirm"]["off"]["correct"] == out["confirm"]["on"]["correct"] == 12
    assert out["confirm"]["fixed"] == [] and out["confirm"]["new_errors"] == []
    assert out["robustness"]["changed_vs_off"] == []
    assert CopilotConfig().use_wordnet_noun_sense is False


def test_heldout_unchanged_and_safe():
    rob = _confirm()["robustness"]
    for arm in ("off", "on"):
        h = rob[arm]["per_synonym_split"]["heldout"]
        assert round(h["perturbed_accuracy"], 3) == 0.514
        assert h["by_gate"]["ANSWER"]["correct"] == 0
        assert rob[arm]["clean_accuracy"] == 1.0
        assert rob[arm]["n_fail_open"] == rob[arm]["n_spurious_write"] == rob[arm]["n_raw_pii_outputs"] == 0


def test_fresh_set_arm_for_the_dev2_choice_is_recorded_and_safe():
    out = json.loads((ART / "synonym_fresh_eval.json").read_text())
    arm = out["configs"]["+ WordNet noun senses, dev2-chosen (lone, path 1, first sense; ships off)"]
    assert arm["n"] - len(arm["wrong"]) == 8 and arm["answer_correct"] == "1/11"
    assert arm["n_fail_open"] == 0 and arm["n_spurious_write"] == 0
