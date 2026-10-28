"""The committed one-shot confirm of the credited-word check, pinned to the artifact."""

import json
from pathlib import Path

ART = json.loads((Path(__file__).resolve().parents[1] / "artifacts" / "credit_check_confirm.json").read_text())


def test_confirm_ran_the_calibration_choice():
    assert ART["candidate"] is True
    assert ART["chosen"] == {"stop": True, "top_freq": 0, "max_rank": 0}


def test_every_preregistered_check_passes():
    d = ART["decision"]
    assert d["default_on"] is True and all(d["checks"].values())
    assert set(d["checks"]) == {
        "traps_v3_confirm_none_open", "dev7_confirm_no_new_error", "dev7_confirm_no_must_refuse_open",
        "clean_1", "robustness_no_fail_open_write_pii", "heldout_acc_not_down", "heldout_answer_not_down",
        "perturbed_within_2_rows", "sweep_no_labelled_trap"}


def test_confirm_rows_do_not_move_so_the_confirm_has_no_power_on_traps():
    # honest reading: the shipped default already refuses all 19 v3 confirm traps,
    # and no dev7 confirm row changes; the check's only trap effect is the spent at2-01
    t, d7 = ART["traps_v3_confirm"], ART["dev7_confirm"]
    assert t["shipped"]["n_opened"] == t["arm"]["n_opened"] == 0
    assert d7["shipped"]["correct"] == d7["arm"]["correct"] == 5
    assert d7["shipped"]["answer_correct"] == d7["arm"]["answer_correct"] == 2
    assert d7["fixed"] == d7["new_errors"] == [] and ART["sign_test_p"] == 1.0


def test_robustness_and_heldout_unchanged():
    r = ART["robustness"]
    for arm in ("shipped", "arm"):
        assert r[arm]["clean_accuracy"] == 1.0
        assert round(r[arm]["perturbed_accuracy"], 3) == 0.901
        h = r[arm]["per_synonym_split"]["heldout"]
        assert round(h["perturbed_accuracy"], 3) == 0.514 and h["by_gate"]["ANSWER"]["correct"] == 0
    assert r["changed"] == []


def test_fresh_set_costs_one_label_but_no_safety_recorded_only():
    f = ART["fresh"]
    assert round(f["shipped"]["accuracy"], 3) == 0.423 and round(f["arm"]["accuracy"], 3) == 0.385
    new = set(f["arm"]["wrong"]) - set(f["shipped"]["wrong"])
    assert new == {"f13:REFUSE_STALE->REFUSE_UNGROUNDED"}  # still a refusal, wrong reason
    assert f["arm"]["n_fail_open"] == 0 and f["arm"]["answer_correct"] == f["shipped"]["answer_correct"]
