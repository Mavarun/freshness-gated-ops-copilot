"""Pre-registered dev4 protocol for unknown-words-only Datamuse (no grid runs)."""

from ops_copilot.config import CopilotConfig
from ops_copilot.datamuse_dev4 import (
    DEFAULTS,
    calibration_rows,
    config_for,
    confirm_decision,
    grid_settings,
    is_safe_setting,
    knobs_off_default,
    opened_must_refuse,
    selection_key,
)
from ops_copilot.synonym_dev3 import load_dev3
from ops_copilot.synonym_dev4 import half
from ops_copilot.synonym_split import load_split


def _r(**kw):
    base = {"safe": True, "calib_correct": 80, "calib_answer_correct": 40,
            "max_rank": 10, "max_neighbours": 1, "context_min": 0}
    return {**base, **kw}


def test_grid_is_24_unique_settings_with_the_posthoc_arm_inside():
    g = grid_settings()
    assert len(g) == 24 and len({tuple(sorted(s.items())) for s in g}) == 24
    assert {"max_rank": 50, "max_neighbours": 2, "context_min": 2} in g


def test_every_arm_maps_unknown_words_only_and_the_shipped_flag_is_off():
    assert CopilotConfig().use_datamuse_ml is False
    assert DEFAULTS == {"max_rank": 10, "max_neighbours": 1, "context_min": 0}
    for st in grid_settings():
        cfg = config_for(st)
        assert cfg.use_datamuse_ml and cfg.datamuse_scope == "lone"
        assert cfg.datamuse_expand_known is False and cfg.datamuse_noun_only is False
        assert cfg.use_wordnet_noun_sense is False and cfg.use_noun_gloss_sense is False


def test_selection_order():
    assert selection_key(_r(safe=False, calib_correct=99)) > selection_key(_r())
    assert selection_key(_r(calib_correct=81, max_rank=100, context_min=2)) < selection_key(_r())
    assert min([_r(max_rank=20), _r()], key=selection_key)["max_rank"] == 10
    assert min([_r(max_rank=20, context_min=1), _r(max_rank=20, context_min=2)],
               key=selection_key)["context_min"] == 2
    assert knobs_off_default(_r(max_rank=50, context_min=1)) == 2


def test_calibration_rows_hold_dev4_tune_but_never_dev4_confirm_or_heldout():
    rows = calibration_rows()
    ids = {r["id"] for r in rows}
    assert not ids & {r["id"] for r in half("confirm")}
    assert {r["id"] for r in half("tune")} <= ids and {r["id"] for r in load_dev3()} <= ids
    heldout = {k for k, v in load_split()["rows"].items() if v["split"] == "heldout"}
    assert not ids & heldout
    assert len(rows) == 15 + 43 + 45 + 23


def test_must_refuse_opening_and_the_sweep_each_make_a_setting_unsafe():
    rows = [{"id": "a", "expect_decision": "REFUSE_UNGROUNDED"}, {"id": "b", "expect_decision": "ANSWER"}]
    stats = {"decisions": {"a": "ANSWER", "b": "ANSWER"}}
    assert opened_must_refuse(stats, rows) == ["a"]
    assert opened_must_refuse({"decisions": {"a": "REFUSE_STALE", "b": "ANSWER"}}, rows) == []
    assert is_safe_setting(True, [], {"safe": True})
    assert not is_safe_setting(True, ["a"], {"safe": True})
    assert not is_safe_setting(True, [], {"safe": False})
    assert not is_safe_setting(False, [], {"safe": True})


def _rob(acc, ans):
    return {"clean_accuracy": 1.0, "n_fail_open": 0, "n_spurious_write": 0, "n_raw_pii_outputs": 0,
            "per_synonym_split": {"heldout": {"perturbed_accuracy": acc, "by_gate": {"ANSWER": {"correct": ans}}}}}


def _conf(dec):
    ok = {k: v == e for (k, v), e in zip(dec.items(), ("ANSWER", "REFUSE_UNGROUNDED"))}
    return {"correct": sum(ok.values()), "answer_correct": int(ok["x"]), "n_fail_open": 0,
            "n_spurious_write": 0, "n_raw_pii": 0, "ok": ok, "decisions": dec}


def test_confirm_needs_the_base_rule_and_both_no_new_error_checks():
    rows = [{"id": "x", "expect_decision": "ANSWER"}, {"id": "t", "expect_decision": "REFUSE_UNGROUNDED"}]
    off = _conf({"x": "REFUSE_UNGROUNDED", "t": "REFUSE_UNGROUNDED"})
    good = _conf({"x": "ANSWER", "t": "REFUSE_UNGROUNDED"})
    d = confirm_decision(off, good, _rob(0.5, 0), _rob(0.5, 0), rows, {"safe": True})
    assert d["default_on"] and d["must_refuse_opened"] == []
    assert not confirm_decision(off, good, _rob(0.5, 0), _rob(0.5, 0), rows, {"safe": False})["default_on"]
    bad = _conf({"x": "ANSWER", "t": "ANSWER"})
    d = confirm_decision(off, bad, _rob(0.5, 0), _rob(0.5, 0), rows, {"safe": True})
    assert not d["default_on"] and d["must_refuse_opened"] == ["t"]
    assert not d["checks"]["confirm_must_refuse_held"]
