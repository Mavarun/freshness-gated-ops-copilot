"""Passage-support calibration: dev-only rows, pre-registered selection, artifact."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from ops_copilot.config import CopilotConfig
from ops_copilot.passage_support_calibration import (
    GRID,
    MAX_TERMS,
    SCOPES,
    STRICT,
    recommend_default_on,
    select,
)
from ops_copilot.semantic_calibration import calibration_rows
from ops_copilot.synonym_split import load_split, row_splits

ART = Path(__file__).resolve().parents[1] / "artifacts" / "passage_support_calibration.json"


def _artifact() -> dict:
    return json.loads(ART.read_text(encoding="utf-8"))


def test_calibration_never_scores_heldout_rows() -> None:
    splits = row_splits()
    ids = _artifact()["calibration_rows"]
    assert len(ids) == 66
    assert not [rid for rid in ids if splits.get(rid) == "heldout"]
    assert ids == [rid for rid, _, _ in calibration_rows()]


def test_dev_word_report_uses_dev_words_only() -> None:
    dev = set(load_split()["dev_words"])
    held = set(load_split()["heldout_words"])
    words = {w["word"] for w in _artifact()["dev_words"]}
    assert words <= dev and not words & held


def test_artifact_covers_the_whole_grid() -> None:
    res = _artifact()["results"]
    assert len(res) == len(GRID) * len(MAX_TERMS) * len(SCOPES) * len(STRICT)


def _r(acc, th, *, strict=True, known=False, mt=1, clean=1.0, fo=0, sp=0):
    return {
        "min_prob": th, "strict": strict, "known_words": known, "max_terms": mt,
        "accuracy": acc, "clean_accuracy": clean, "n_fail_open": fo,
        "n_spurious_write": sp, "n_raw_pii_outputs": 0,
    }


def test_selection_is_safety_then_accuracy_then_strict_narrow_then_max_margin() -> None:
    res = [
        _r(0.99, 0.05, fo=1),
        _r(0.98, 0.075, sp=1),
        _r(0.97, 0.1, clean=0.98),
        _r(0.95, 0.2, strict=False),
        _r(0.95, 0.2, known=True, mt=2),
        _r(0.95, 0.2, known=True),
        _r(0.95, 0.225, known=True),
        _r(0.95, 0.25, known=True),
        _r(0.95, 0.5, known=True),
    ]
    c = select(res)
    assert (c["strict"], c["known_words"], c["max_terms"]) == (True, True, 1)
    assert c["optimal_run"] == [0.2, 0.25] and c["min_prob"] == 0.225
    with pytest.raises(RuntimeError):
        select([_r(1.0, 0.1, fo=1)])


def test_default_on_needs_a_strict_dev_gain() -> None:
    assert not recommend_default_on({"accuracy": 0.9}, {"accuracy": 0.9})
    assert recommend_default_on({"accuracy": 0.9}, {"accuracy": 0.91})


def test_artifact_choice_is_the_config_setting() -> None:
    chosen = _artifact()["chosen"]
    cfg = CopilotConfig()
    assert cfg.passage_support_min_prob == chosen["min_prob"]
    assert cfg.passage_support_max_terms == chosen["max_terms"]
    assert cfg.passage_support_known_words == chosen["known_words"]
    assert cfg.passage_support_strict == chosen["strict"]


def test_chosen_setting_is_safe_on_the_calibration_rows() -> None:
    art = _artifact()
    c = art["chosen"]
    row = next(
        r for r in art["results"]
        if r["min_prob"] == c["min_prob"] and r["strict"] == c["strict"]
        and r["known_words"] == c["known_words"] and r["max_terms"] == c["max_terms"]
    )
    assert row["clean_accuracy"] == 1.0 and row["n_fail_open"] == 0 and row["n_spurious_write"] == 0
    assert row["accuracy"] > art["baseline_off"]["accuracy"]
