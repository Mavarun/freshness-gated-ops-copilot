"""Answer-support calibration: dev-only rows, pre-registered selection, artifact."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from ops_copilot.answer_support_calibration import (
    GRID,
    MAX_TERMS,
    SCOPES,
    STRICT,
    recommend_default_on,
    select,
)
from ops_copilot.config import CopilotConfig
from ops_copilot.semantic_calibration import calibration_rows
from ops_copilot.synonym_split import row_splits

ART = Path(__file__).resolve().parents[1] / "artifacts" / "answer_support_calibration.json"


def _artifact() -> dict:
    return json.loads(ART.read_text(encoding="utf-8"))


def test_calibration_never_scores_heldout_rows() -> None:
    splits = row_splits()
    ids = _artifact()["calibration_rows"]
    assert len(ids) == 66
    assert not [rid for rid in ids if splits.get(rid) == "heldout"]
    assert ids == [rid for rid, _, _ in calibration_rows()]


def test_artifact_covers_the_whole_grid() -> None:
    res = _artifact()["results"]
    assert len(res) == len(GRID) * len(MAX_TERMS) * len(SCOPES) * len(STRICT)


def _r(acc, th, *, strict=True, known=False, mt=1, clean=1.0, fo=0, sp=0):
    return {
        "min_score": th, "strict": strict, "known_words": known, "max_terms": mt,
        "accuracy": acc, "clean_accuracy": clean, "n_fail_open": fo,
        "n_spurious_write": sp, "n_raw_pii_outputs": 0,
    }


def test_selection_is_safety_then_accuracy_then_strict_narrow_then_max_margin() -> None:
    res = [
        _r(0.99, 1.0, fo=1),  # unsafe
        _r(0.98, 1.25, sp=1),  # spurious write
        _r(0.97, 1.5, clean=0.98),  # breaks a clean row
        _r(0.95, 2.0, strict=False),
        _r(0.95, 2.0, known=True, mt=2),
        _r(0.95, 2.0, known=True),
        _r(0.95, 2.25, known=True),
        _r(0.95, 2.5, known=True),
        _r(0.95, 3.5, known=True),
    ]
    c = select(res)
    assert (c["strict"], c["known_words"], c["max_terms"]) == (True, True, 1)
    assert c["optimal_run"] == [2.0, 2.5] and c["min_score"] == 2.25
    with pytest.raises(RuntimeError):
        select([_r(1.0, 1.0, fo=1)])


def test_default_on_needs_a_strict_dev_gain() -> None:
    assert not recommend_default_on({"accuracy": 0.9}, {"accuracy": 0.9})
    assert recommend_default_on({"accuracy": 0.9}, {"accuracy": 0.91})


def test_artifact_choice_is_the_config_setting_and_stays_off_by_default() -> None:
    chosen = _artifact()["chosen"]
    cfg = CopilotConfig()
    assert cfg.answer_support_min_score == chosen["min_score"]
    assert cfg.answer_support_max_terms == chosen["max_terms"]
    assert cfg.answer_support_known_words == chosen["known_words"]
    assert cfg.answer_support_strict == chosen["strict"]
    assert cfg.use_answer_support_model is False  # decided by the held-out run


def test_dev_gain_is_one_pii_row_and_no_clean_row_moves() -> None:
    art = _artifact()
    off = set(art["baseline_off"]["wrong"])
    chosen = art["chosen"]
    row = next(
        r for r in art["results"]
        if r["min_score"] == chosen["min_score"] and r["strict"] == chosen["strict"]
        and r["known_words"] == chosen["known_words"] and r["max_terms"] == chosen["max_terms"]
    )
    assert off - set(row["wrong"]) == {"g48-synonym:REFUSE_PII->REFUSE_UNGROUNDED"}
    assert not set(row["wrong"]) - off
    assert row["clean_accuracy"] == 1.0
