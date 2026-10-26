"""The recorded one-shot dev6 confirm: numbers pinned, decision consistent with the rule."""

import json
from pathlib import Path

from ops_copilot.config import CopilotConfig
from ops_copilot.datamuse_dev6 import ARM, confirm_decision

ART = Path(__file__).resolve().parents[1] / "artifacts"


def _out() -> dict:
    return json.loads((ART / "datamuse_dev6_confirm.json").read_text())


def test_confirm_numbers_are_pinned():
    out = _out()
    c = out["confirm"]
    assert out["arm"] == ARM
    assert (c["off"]["correct"], c["on"]["correct"], c["off"]["n"]) == (21, 23, 45)
    assert (c["off"]["answer_correct"], c["on"]["answer_correct"], c["on"]["n_answer"]) == (3, 5, 24)
    assert c["fixed"] == ["d6-11", "d6-24", "d6-27"] and c["new_errors"] == ["d6-36"]
    assert c["must_refuse_opened_off"] == [] and c["must_refuse_opened_on"] == ["d6-36"]
    assert out["traps"]["off"]["n_opened"] == out["traps"]["on"]["n_opened"] == 0
    assert round(out["sign_test_p"], 3) == 0.625


def test_heldout_moves_only_in_the_arm_that_ships_off():
    r = _out()["robustness"]
    ho, hn = (r[a]["per_synonym_split"]["heldout"] for a in ("off", "on"))
    assert round(ho["perturbed_accuracy"], 3) == 0.514 and ho["by_gate"]["ANSWER"]["correct"] == 0
    assert round(hn["perturbed_accuracy"], 3) == 0.600 and hn["by_gate"]["ANSWER"]["correct"] == 1
    assert r["off"]["clean_accuracy"] == r["on"]["clean_accuracy"] == 1.0


def test_decision_is_off_for_the_pre_registered_reasons_and_the_flag_stays_off():
    out = _out()
    d = out["decision"]
    assert d["default_on"] is False
    failed = sorted(k for k, v in d["checks"].items() if not v)
    assert failed == ["confirm_must_refuse_held", "confirm_no_fail_open_write_pii", "confirm_no_new_error"]
    assert d["must_refuse_opened"] == ["d6-36"]
    assert CopilotConfig().use_datamuse_ml is False


def test_recorded_decision_reproduces_from_the_recorded_stats():
    out = _out()
    c, r = out["confirm"], out["robustness"]
    ok = lambda s: {k: s["decisions"][k] == v for k, v in _labels().items()}  # noqa: E731
    off = {**c["off"], "ok": ok(c["off"])}
    on = {**c["on"], "ok": ok(c["on"])}
    rows = [{"id": k, "expect_decision": v} for k, v in _labels().items()]
    again = confirm_decision(off, on, r["off"], r["on"], rows, {"safe": not out["sweep"]["labelled_trap_opened"]},
                             out["traps"]["on"])
    assert again["checks"] == out["decision"]["checks"]


def _labels() -> dict:
    from ops_copilot.synonym_dev6 import load_dev6

    return {r["id"]: r["expect_decision"] for r in load_dev6()}
