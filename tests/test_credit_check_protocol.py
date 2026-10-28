"""Pre-registered protocol of the credited-word check (no unseen row is scored here)."""

from ops_copilot.config import CopilotConfig
from ops_copilot.credit_check import (
    MAX_ANSWER_LOST,
    MAX_ROWS_LOST,
    calibration_rows,
    calibration_traps,
    config_for,
    confirm_decision,
    grid_settings,
    is_safe_setting,
    selection_key,
    shipped_config,
)
from ops_copilot.attribute_traps_v3 import half_v3
from ops_copilot.synonym_dev7 import half as dev7_half


def test_grid_is_31_arms_without_all_off():
    g = grid_settings()
    assert len(g) == 31
    assert {"stop": False, "top_freq": 0, "max_rank": 0} not in g


def test_baseline_is_the_shipped_default_and_arms_only_touch_credit_knobs():
    # the pre-change default (credited-word check off) stays the baseline after the flip
    from dataclasses import replace

    assert shipped_config() == replace(CopilotConfig(), passage_support_credit_stop=False)
    cfg = config_for({"stop": True, "top_freq": 100, "max_rank": 500})
    assert (cfg.passage_support_credit_stop, cfg.passage_support_credit_top_freq,
            cfg.passage_support_credit_max_rank) == (True, 100, 500)
    assert cfg.passage_support_null_min == 0.30 and cfg.passage_support_null_seed == 42


def test_calibration_never_contains_a_confirm_row():
    rows, traps = calibration_rows(), calibration_traps()
    assert len(rows) == 171 + 45 + 22 and len(traps) == 36 + 40 + 19
    ids = {r["id"] for r in rows} | {r["id"] for r in traps}
    assert not ids & {r["id"] for r in dev7_half("confirm")}
    assert not ids & {r["id"] for r in half_v3("confirm")}
    assert "at2-01" in ids  # the open trap must close in calibration


def _r(**kw):
    base = dict(stop=False, top_freq=0, max_rank=500, clean_accuracy=1.0, n_fail_open_clean=0,
                n_spurious_write=0, n_raw_pii=0, must_refuse_opened=[], traps_opened=[], sweep_safe=True,
                rows_lost=0, answer_lost=0, calib_correct=100, calib_answer_correct=30)
    base.update(kw)
    base["safe"] = is_safe_setting(base)
    return base


def test_safety_rule():
    assert _r()["safe"]
    assert not _r(traps_opened=["at2-01"])["safe"]
    assert not _r(rows_lost=MAX_ROWS_LOST + 1)["safe"]
    assert not _r(answer_lost=MAX_ANSWER_LOST + 1)["safe"]
    assert not _r(must_refuse_opened=["d7-38"])["safe"]


def test_selection_prefers_accuracy_then_fewer_checks_then_looser():
    a = _r(calib_correct=101, stop=True, top_freq=50)
    b = _r(calib_correct=100, stop=True)
    assert sorted([b, a], key=selection_key)[0] is a
    c, d = _r(stop=True), _r(stop=True, top_freq=50)
    assert sorted([d, c], key=selection_key)[0] is c
    e, f = _r(max_rank=2000), _r(max_rank=500)
    assert sorted([f, e], key=selection_key)[0] is e
    g = _r(stop=False, max_rank=0, top_freq=100)
    assert sorted([g, _r(stop=False, max_rank=0, top_freq=50)], key=selection_key)[0]["top_freq"] == 50


def _rob(acc=0.9, h_acc=0.514, h_ans=0, clean=1.0):
    return {"clean_accuracy": clean, "perturbed_accuracy": acc, "n_perturbed": 203, "n_fail_open": 0,
            "n_spurious_write": 0, "n_raw_pii_outputs": 0,
            "per_synonym_split": {"heldout": {"perturbed_accuracy": h_acc, "by_gate": {"ANSWER": {"correct": h_ans}}}}}


def test_confirm_needs_no_new_dev7_error_and_no_trap():
    rows = [{"id": "x", "expect_decision": "ANSWER"}, {"id": "y", "expect_decision": "REFUSE_UNGROUNDED"}]
    ok = {"ok": {"x": True, "y": True}, "decisions": {"x": "ANSWER", "y": "REFUSE_UNGROUNDED"}}
    broke = {"ok": {"x": False, "y": True}, "decisions": {"x": "REFUSE_UNGROUNDED", "y": "REFUSE_UNGROUNDED"}}
    sw = {"safe": True}
    assert confirm_decision({"n_opened": 0}, ok, ok, rows, _rob(), _rob(), sw)["default_on"]
    d = confirm_decision({"n_opened": 0}, ok, broke, rows, _rob(), _rob(), sw)
    assert not d["default_on"] and d["dev7_new_errors"] == ["x"]
    assert not confirm_decision({"n_opened": 1}, ok, ok, rows, _rob(), _rob(), sw)["default_on"]
    assert not confirm_decision({"n_opened": 0}, ok, ok, rows, _rob(h_ans=1), _rob(h_ans=0), sw)["default_on"]
