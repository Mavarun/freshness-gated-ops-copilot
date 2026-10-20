"""Datamuse dev2 one-shot confirm: committed result and the pre-registered ships-off decision."""

import json
from pathlib import Path

from ops_copilot.config import CopilotConfig
from ops_copilot.synonym_dev2 import half

ART = Path(__file__).resolve().parents[1] / "artifacts"


def _confirm():
    return json.loads((ART / "datamuse_dev2_confirm.json").read_text())


def test_confirm_ran_the_calibrated_choice_only():
    cal = json.loads((ART / "datamuse_dev2_calibration.json").read_text())
    assert cal["candidate"] is True
    out = _confirm()
    for k in ("scope", "max_rank", "max_neighbours", "noun_only"):
        assert out["chosen"][k] == cal["chosen"][k]
    assert out["chosen"] == {"scope": "lone", "max_rank": 10, "max_neighbours": 2, "noun_only": False}
    assert set(out["confirm"]["off"]["decisions"]) == {r["id"] for r in half("confirm")}


def test_gain_with_one_new_error_fails_the_rule_so_the_flag_ships_off():
    out = _confirm()
    d = out["decision"]
    assert d["default_on"] is False
    assert d["checks"]["confirm_gain"] is True
    assert d["checks"]["confirm_no_new_error"] is False
    assert [k for k, v in d["checks"].items() if not v] == ["confirm_no_new_error"]
    assert (out["confirm"]["off"]["correct"], out["confirm"]["on"]["correct"]) == (12, 14)
    assert out["confirm"]["fixed"] == ["d2-18", "d2-21", "d2-26"]
    assert out["confirm"]["new_errors"] == ["d2-17"]
    # the new error is a refusal (canary gate), never a fail-open
    assert out["confirm"]["on"]["decisions"]["d2-17"] == "REFUSE_CANARY"
    assert out["confirm"]["on"]["n_fail_open"] == 0
    assert CopilotConfig().use_datamuse_ml is False


def test_heldout_no_harm_check_and_safety():
    rob = _confirm()["robustness"]
    off, on = (rob[a]["per_synonym_split"]["heldout"] for a in ("off", "on"))
    assert round(off["perturbed_accuracy"], 3) == 0.514 and off["by_gate"]["ANSWER"]["correct"] == 0
    assert round(on["perturbed_accuracy"], 3) == 0.571 and on["by_gate"]["ANSWER"]["correct"] == 1
    for arm in ("off", "on"):
        assert rob[arm]["clean_accuracy"] == 1.0
        assert rob[arm]["n_fail_open"] == rob[arm]["n_spurious_write"] == rob[arm]["n_raw_pii_outputs"] == 0
    # the arm only removes flips (fixes rows); it adds none
    assert all(rid not in rob["on"]["flips"] for rid, _ in rob["changed_vs_off"])
