"""Pre-registered dev5 protocol for the word-meaning-gated Datamuse arm (no grid runs)."""

from ops_copilot.config import CopilotConfig
from ops_copilot.datamuse_dev5 import (
    DEV4_CHOSEN,
    calibration_rows,
    config_for,
    grid_settings,
    selection_key,
)
from ops_copilot.synonym_dev4 import load_dev4
from ops_copilot.synonym_dev5 import half
from ops_copilot.synonym_split import load_split


def _r(**kw):
    base = {"safe": True, "calib_correct": 120, "calib_answer_correct": 60,
            "max_rank": 50, "max_neighbours": 1, "context_min": 0, "sense_min": 0.4}
    return {**base, **kw}


def test_grid_is_48_unique_settings_every_one_with_the_sense_gate_on():
    g = grid_settings()
    assert len(g) == 48 and len({tuple(sorted(s.items())) for s in g}) == 48
    assert {s["sense_min"] for s in g} == {0.30, 0.40, 0.50, 0.60}
    assert all(s["sense_min"] > 0 for s in g)
    assert DEV4_CHOSEN not in g and DEV4_CHOSEN["sense_min"] == 0.0


def test_every_arm_maps_unknown_words_only_and_the_shipped_flag_is_off():
    assert CopilotConfig().use_datamuse_ml is False and CopilotConfig().datamuse_sense_min == 0.0
    for st in grid_settings():
        cfg = config_for(st)
        assert cfg.use_datamuse_ml and cfg.datamuse_scope == "lone"
        assert cfg.datamuse_expand_known is False and cfg.datamuse_noun_only is False
        assert cfg.datamuse_sense_min == st["sense_min"]
        assert cfg.use_wordnet_noun_sense is False and cfg.use_noun_gloss_sense is False


def test_selection_order_prefers_the_stricter_gate_on_ties():
    assert selection_key(_r(safe=False, calib_correct=999)) > selection_key(_r())
    assert selection_key(_r(calib_correct=121, sense_min=0.3)) < selection_key(_r())
    assert min([_r(sense_min=0.3), _r(sense_min=0.6)], key=selection_key)["sense_min"] == 0.6
    assert min([_r(max_rank=100), _r(max_rank=20)], key=selection_key)["max_rank"] == 20
    assert min([_r(context_min=0), _r(context_min=2)], key=selection_key)["context_min"] == 2


def test_calibration_rows_hold_all_dev4_and_dev5_tune_but_never_dev5_confirm_or_heldout():
    rows = calibration_rows()
    ids = {r["id"] for r in rows}
    assert not ids & {r["id"] for r in half("confirm")}
    assert {r["id"] for r in half("tune")} <= ids and {r["id"] for r in load_dev4()} <= ids
    assert "d4-37" in ids  # the PR #27 trap is a calibration must-refuse row now
    heldout = {k for k, v in load_split()["rows"].items() if v["split"] == "heldout"}
    assert not ids & heldout
    assert len(rows) == 15 + 43 + 45 + 44 + 24 == 171
