"""Pre-registered dev3 protocol for the context-gated Datamuse arm (no runs)."""

from ops_copilot.config import CopilotConfig
from ops_copilot.datamuse_dev3 import (
    DEFAULTS,
    calibration_rows,
    config_for,
    grid_settings,
    knobs_off_default,
    selection_key,
)
from ops_copilot.synonym_dev2 import load_dev2
from ops_copilot.synonym_dev3 import half
from ops_copilot.synonym_split import load_split


def _r(**kw):
    base = {"safe": True, "calib_correct": 60, "calib_answer_correct": 30, "scope": "known",
            "max_rank": 10, "max_neighbours": 1, "context_min": 0}
    return {**base, **kw}


def test_grid_is_48_unique_settings_with_the_shelved_dev2_arm_inside():
    g = grid_settings()
    assert len(g) == 48 and len({tuple(sorted(s.items())) for s in g}) == 48
    assert {"scope": "lone", "max_rank": 10, "max_neighbours": 2, "context_min": 0} in g
    assert not any(s["scope"] == "all" for s in g)


def test_defaults_come_from_the_shipped_config_and_the_flag_stays_off():
    cfg = CopilotConfig()
    assert cfg.use_datamuse_ml is False
    assert DEFAULTS == {"max_rank": 10, "max_neighbours": 1, "context_min": 0}


def test_config_for_sets_only_datamuse_knobs():
    cfg = config_for({"scope": "lone", "max_rank": 50, "max_neighbours": 2, "context_min": 1})
    assert cfg.use_datamuse_ml and cfg.datamuse_scope == "lone" and cfg.datamuse_context_min == 1
    assert (cfg.datamuse_max_rank, cfg.datamuse_max_neighbours, cfg.datamuse_noun_only) == (50, 2, False)
    assert cfg.use_wordnet_noun_sense is False and cfg.use_noun_gloss_sense is False


def test_selection_order():
    assert selection_key(_r(safe=False, calib_correct=90)) > selection_key(_r())
    assert selection_key(_r(calib_correct=61, max_rank=100, context_min=2)) < selection_key(_r())
    assert selection_key(_r(scope="lone")) > selection_key(_r(max_rank=100))
    # ties: defaults first, then the more restrictive value (higher context_min)
    assert min([_r(max_rank=20), _r()], key=selection_key)["max_rank"] == 10
    assert min([_r(max_rank=20, context_min=1), _r(max_rank=20, context_min=2)],
               key=selection_key)["context_min"] == 2
    assert knobs_off_default(_r(max_rank=50, context_min=1)) == 2


def test_calibration_rows_are_dev_all_of_dev2_and_dev3_calib_only():
    rows = calibration_rows()
    ids = {r["id"] for r in rows}
    assert not ids & {r["id"] for r in half("confirm")}
    assert {r["id"] for r in load_dev2()} <= ids
    heldout = {k for k, v in load_split()["rows"].items() if v["split"] == "heldout"}
    assert not ids & heldout
    assert len(rows) == 15 + 43 + 25
