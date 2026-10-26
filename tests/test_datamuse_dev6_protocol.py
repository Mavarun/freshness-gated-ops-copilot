"""Pre-registered dev6 confirm protocol (no dev6 row is scored here)."""

import json
from pathlib import Path

import pytest

from ops_copilot.config import CopilotConfig
from ops_copilot.datamuse_dev6 import ARM, arm_config, confirm_decision, off_config, sign_test_p

ART = Path(__file__).resolve().parents[1] / "artifacts"


def test_arm_is_the_recalibration_choice_and_a_candidate():
    rec = json.loads((ART / "datamuse_dev5_recalibration.json").read_text())
    assert rec["candidate"] is True
    assert {k: rec["chosen"][k] for k in ARM} == ARM


def test_arm_config_maps_unknown_words_only_on_top_of_the_shipped_default():
    cfg, ship = arm_config(), CopilotConfig()
    assert cfg.use_datamuse_ml and cfg.datamuse_scope == "lone" and not cfg.datamuse_expand_known
    assert (cfg.datamuse_max_rank, cfg.datamuse_max_neighbours, cfg.datamuse_context_min,
            cfg.datamuse_sense_min) == (100, 1, 2, 0.30)
    assert cfg.passage_support_null_min == ship.passage_support_null_min == 0.30
    assert cfg.passage_support_null_sticky and ship.passage_support_null_sticky
    assert not off_config().use_datamuse_ml


def test_sign_test_is_exact_and_two_sided():
    assert sign_test_p(0, 0) == 1.0
    assert sign_test_p(1, 0) == 1.0
    assert sign_test_p(5, 0) == pytest.approx(2 / 32)
    assert sign_test_p(0, 5) == sign_test_p(5, 0)
    assert sign_test_p(6, 1) == pytest.approx(2 * 8 / 128)


def _s(correct, answer, ok=None, decisions=None, n_fail_open=0):
    ok = ok or {"a": True}
    return {"n": len(ok), "correct": correct, "answer_correct": answer, "n_fail_open": n_fail_open,
            "n_spurious_write": 0, "n_raw_pii": 0, "ok": ok, "decisions": decisions or {"a": "ANSWER"}}


def _rob(acc=0.5, ans=0):
    return {"clean_accuracy": 1.0, "n_fail_open": 0, "n_spurious_write": 0, "n_raw_pii_outputs": 0,
            "per_synonym_split": {"heldout": {"perturbed_accuracy": acc, "by_gate": {"ANSWER": {"correct": ans}}}}}


def test_decision_needs_every_check_including_the_attribute_traps():
    rows = [{"id": "a", "expect_decision": "ANSWER"}, {"id": "b", "expect_decision": "REFUSE_UNGROUNDED"}]
    off = _s(1, 0, ok={"a": False, "b": True}, decisions={"a": "REFUSE_UNGROUNDED", "b": "REFUSE_UNGROUNDED"})
    on = _s(2, 1, ok={"a": True, "b": True}, decisions={"a": "ANSWER", "b": "REFUSE_UNGROUNDED"})
    sweep_ok = {"safe": True}
    clean_traps = {"n_opened": 0, "opened": []}
    good = confirm_decision(off, on, _rob(), _rob(), rows, sweep_ok, clean_traps)
    assert good["default_on"] and all(good["checks"].values())
    bad = confirm_decision(off, on, _rob(), _rob(), rows, sweep_ok, {"n_opened": 1, "opened": ["at-03"]})
    assert not bad["default_on"] and bad["checks"]["attribute_traps_all_refused"] is False
    assert bad["traps_opened"] == ["at-03"]


def test_a_must_refuse_open_or_no_gain_ships_off():
    rows = [{"id": "a", "expect_decision": "ANSWER"}, {"id": "b", "expect_decision": "REFUSE_UNGROUNDED"}]
    off = _s(1, 1, ok={"a": True, "b": True}, decisions={"a": "ANSWER", "b": "REFUSE_UNGROUNDED"})
    opened = _s(1, 1, ok={"a": True, "b": False}, decisions={"a": "ANSWER", "b": "ANSWER"}, n_fail_open=1)
    d = confirm_decision(off, opened, _rob(), _rob(), rows, {"safe": True}, {"n_opened": 0, "opened": []})
    assert not d["default_on"] and d["must_refuse_opened"] == ["b"]
    assert not d["checks"]["confirm_gain"] and not d["checks"]["confirm_no_new_error"]
