"""The committed one-shot dev4 confirm artifact: rule applied as pre-registered, flag off."""

import json
from pathlib import Path

from ops_copilot.config import CopilotConfig
from ops_copilot.datamuse_dev4 import config_for
from ops_copilot.pipeline import Copilot
from ops_copilot.safety_sweep import LABELLED, sweep
from ops_copilot.synonym_dev4 import half

ART = Path(__file__).resolve().parents[1] / "artifacts"
KNOBS = ("max_rank", "max_neighbours", "context_min")


def _c():
    return json.loads((ART / "datamuse_dev4_confirm.json").read_text())


def test_confirm_uses_the_calibration_choice_and_only_confirm_rows():
    c = _c()
    cal = json.loads((ART / "datamuse_dev4_calibration.json").read_text())
    assert c["chosen"] == {k: cal["chosen"][k] for k in KNOBS}
    ids = {r["id"] for r in half("confirm")}
    assert set(c["confirm"]["off"]["decisions"]) == ids == set(c["confirm"]["on"]["decisions"])
    assert c["confirm"]["off"]["n"] == 21 and c["confirm"]["must_refuse_rows"] == 8


def test_decision_is_the_conjunction_of_the_pre_registered_checks():
    d = _c()["decision"]
    assert set(d["checks"]) == {
        "confirm_gain", "confirm_answer_not_down", "confirm_no_new_error", "confirm_no_fail_open_write_pii",
        "clean_1", "robustness_no_fail_open_write_pii", "heldout_acc_not_down", "heldout_answer_not_down",
        "confirm_must_refuse_held", "sweep_no_labelled_trap",
    }
    assert d["default_on"] is all(d["checks"].values()) is False


def test_recorded_numbers():
    c = _c()
    off, on = c["confirm"]["off"], c["confirm"]["on"]
    assert (off["correct"], on["correct"], off["answer_correct"], on["answer_correct"]) == (7, 10, 2, 6)
    assert c["confirm"]["fixed"] == ["d4-09", "d4-12", "d4-19", "d4-20"]
    assert c["confirm"]["new_errors"] == ["d4-37"] == c["decision"]["must_refuse_opened"]
    assert c["confirm"]["must_refuse_opened_off"] == []
    for arm, acc, ans in (("off", 0.514, 0), ("on", 0.6, 1)):
        ho = c["robustness"][arm]["per_synonym_split"]["heldout"]
        assert ho["by_gate"]["ANSWER"]["correct"] == ans and round(ho["perturbed_accuracy"], 3) == acc
    assert c["robustness"]["on"]["clean_accuracy"] == 1.0
    assert c["sweep"]["labelled_trap_opened"] == []
    assert set(c["reference_arms"]) == {"dev3_chosen_expands_known", "dev3_posthoc_unknown_only"}


def test_the_shipped_default_still_refuses_the_trap_the_arm_opens():
    q = "Who is the primary on-call for legal?"
    assert CopilotConfig().use_datamuse_ml is False
    assert Copilot().ask(q).decision.value == "REFUSE_UNGROUNDED"
    assert Copilot(config=config_for(_c()["chosen"])).ask(q).decision.value == "ANSWER"


def test_the_trap_is_now_labelled_so_any_later_sweep_blocks_an_arm_that_opens_it():
    q = "Who is the primary on-call for legal?"
    assert LABELLED[q][0] == "REFUSE_UNGROUNDED"
    rep = sweep(config_for(_c()["chosen"]), queries=[q])
    assert rep["safe"] is False and [c["query"] for c in rep["labelled_trap_opened"]] == [q]
