"""Word-vector calibration: dev-only rows, selection rule, artifact == config."""

from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

from ops_copilot import Copilot, CopilotConfig
from ops_copilot.semantic_calibration import calibration_rows, score
from ops_copilot.synonym_split import load_split, row_splits
from ops_copilot.word_vector_calibration import GRID, dev_pair_report, select

ART = Path(__file__).resolve().parents[1] / "artifacts" / "word_vector_calibration.json"


def _artifact() -> dict:
    return json.loads(ART.read_text(encoding="utf-8"))


def test_calibration_never_scores_heldout_rows() -> None:
    splits = row_splits()
    ids = _artifact()["calibration_rows"]
    assert len(ids) == 66
    assert not [rid for rid in ids if splits.get(rid) == "heldout"]
    assert ids == [rid for rid, _, _ in calibration_rows()]


def test_config_defaults_are_the_calibrated_values() -> None:
    art = _artifact()
    chosen, cfg = art["chosen"], CopilotConfig()
    assert cfg.word_vector_min_similarity == chosen["threshold"]
    assert cfg.word_vector_max_neighbours == chosen["max_neighbours"]
    assert cfg.word_vector_known_words == chosen["known_words"]
    assert chosen["accuracy"] > art["baseline_off"]["accuracy"]
    assert art["default_on"] is True


def test_selection_prefers_safety_then_accuracy_then_narrow_scope() -> None:
    def r(th, acc, *, known=False, k=1, clean=1.0, fo=0):
        return {
            "threshold": th, "known_words": known, "max_neighbours": k, "accuracy": acc,
            "clean_accuracy": clean, "n_fail_open": fo, "n_spurious_write": 0,
            "n_raw_pii_outputs": 0,
        }

    res = [
        r(GRID[0], 0.99, fo=1),  # unsafe: never chosen
        r(GRID[1], 0.95, clean=0.98),  # breaks a clean row
        r(GRID[2], 0.90),
        r(GRID[3], 0.90),
        r(GRID[4], 0.90),
        r(GRID[3], 0.90, known=True),
        r(GRID[10], 0.90),
    ]
    chosen = select(res)
    assert chosen["known_words"] is False and chosen["max_neighbours"] == 1
    assert chosen["optimal_run"] == [GRID[2], GRID[4]] and chosen["threshold"] == GRID[3]


def test_calibrated_setting_is_safe_on_the_calibration_rows() -> None:
    cfg = replace(CopilotConfig(), use_word_vector_backoff=True, use_passage_support_model=False)
    res = score(Copilot(config=cfg), calibration_rows())
    assert res["clean_accuracy"] == 1.0
    assert res["n_fail_open"] == res["n_spurious_write"] == res["n_raw_pii_outputs"] == 0
    assert res["accuracy"] == _artifact()["chosen"]["accuracy"]


def test_dev_pair_report_uses_dev_words_only() -> None:
    heldout = set(load_split()["heldout_words"])
    rows = dev_pair_report()
    assert rows and not {p["word"] for p in rows} & heldout
