"""Pre-registered Datamuse dev2 protocol: grid, tie-break, candidate rule (no runs)."""

from ops_copilot.config import CopilotConfig
from ops_copilot.datamuse_dev2 import (
    DEFAULTS,
    calibrate,
    config_for,
    grid_settings,
    knobs_off_default,
    selection_key,
)
from ops_copilot.synonym_dev2 import half
from ops_copilot.wordnet_dev2 import calibration_rows


def _r(**kw):
    base = {"safe": True, "calib_correct": 30, "calib_answer_correct": 10, "scope": "known",
            "max_rank": 10, "max_neighbours": 1, "noun_only": False}
    return {**base, **kw}


def test_grid_is_sixty_unique_settings_and_contains_the_defaults():
    g = grid_settings()
    assert len(g) == 60
    assert len({tuple(sorted(s.items())) for s in g}) == 60
    assert any(knobs_off_default(s) == 0 for s in g)


def test_defaults_come_from_the_shipped_config():
    cfg = CopilotConfig()
    assert cfg.use_datamuse_ml is False
    assert DEFAULTS == {"max_rank": cfg.datamuse_max_rank, "max_neighbours": cfg.datamuse_max_neighbours,
                        "noun_only": cfg.datamuse_noun_only}


def test_config_for_turns_only_datamuse_on():
    cfg = config_for({"scope": "lone", "max_rank": 5, "max_neighbours": 2, "noun_only": True})
    assert cfg.use_datamuse_ml and cfg.datamuse_scope == "lone"
    assert (cfg.datamuse_max_rank, cfg.datamuse_max_neighbours, cfg.datamuse_noun_only) == (5, 2, True)
    assert cfg.use_wordnet_noun_sense is False and cfg.use_noun_gloss_sense is False


def test_safety_and_accuracy_dominate_the_tie_break():
    assert selection_key(_r(safe=False, calib_correct=40)) > selection_key(_r())
    assert selection_key(_r(calib_correct=31, max_rank=50)) < selection_key(_r())
    assert selection_key(_r(calib_answer_correct=11, scope="all")) < selection_key(_r())


def test_tied_settings_keep_unexercised_knobs_at_their_defaults():
    # equal calibration outcome: the default rank 10 beats the more restrictive rank 3
    tied = [_r(max_rank=3), _r(max_rank=10), _r(max_rank=5, noun_only=True)]
    assert min(tied, key=selection_key)["max_rank"] == 10
    # among non-default values, the more restrictive wins
    assert min([_r(max_rank=50), _r(max_rank=20)], key=selection_key)["max_rank"] == 20
    assert min([_r(scope="lone"), _r(scope="known", max_rank=3)], key=selection_key)["scope"] == "known"


def test_calibration_rows_never_include_confirm_or_heldout_rows():
    ids = {r["id"] for r in calibration_rows()}
    assert not ids & {r["id"] for r in half("confirm")}
    assert {r["set"] for r in calibration_rows()} == {"dev", "dev2_calib"}


def test_no_gain_means_no_candidate():
    one = calibration_rows()[:3]
    rep = calibrate(settings=[{"scope": "known", "max_rank": 3, "max_neighbours": 1, "noun_only": True}], rows=one)
    assert rep["n_settings"] == 1
    if rep["chosen"]["calib_correct"] <= rep["baseline_off"]["correct"]:
        assert rep["candidate"] is False
