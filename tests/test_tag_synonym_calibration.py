"""Tag-synonym calibration: dev-only rows, pre-registered selection, artifact."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from ops_copilot.semantic_calibration import calibration_rows
from ops_copilot.synonym_split import load_split, row_splits
from ops_copilot.tag_synonym_calibration import (
    MAX_NEIGHBOURS,
    MIN_SITES,
    SITE_GRID,
    dev_word_report,
    recommend_default_on,
    select,
)

ART = Path(__file__).resolve().parents[1] / "artifacts" / "tag_synonym_calibration.json"


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
    assert len(res) == len(SITE_GRID) * len(MIN_SITES) * len(MAX_NEIGHBOURS) * 2
    assert {r["sites"] for r in res} == set(SITE_GRID)


def _r(acc, *, sites="all", m=1, known=False, k=1, clean=1.0, fo=0, sp=0):
    return {
        "sites": sites, "min_sites": m, "known_words": known, "max_neighbours": k,
        "accuracy": acc, "clean_accuracy": clean, "n_fail_open": fo,
        "n_spurious_write": sp, "n_raw_pii_outputs": 0,
    }


def test_selection_is_safety_then_accuracy_then_the_narrowest_setting() -> None:
    res = [
        _r(0.99, fo=1),  # unsafe
        _r(0.98, sp=1),  # spurious write
        _r(0.97, clean=0.98),  # breaks a clean row
        _r(0.95, sites="all", m=1),
        _r(0.95, sites="ops", m=1, known=True),
        _r(0.95, sites="ops", m=2, known=True, k=3),
        _r(0.95, sites="ops", m=2, known=False, k=3),
        _r(0.95, sites="ops", m=2, known=False, k=1),
    ]
    c = select(res)
    assert (c["sites"], c["min_sites"], c["known_words"], c["max_neighbours"]) == ("ops", 2, False, 1)
    assert c["n_optimal"] == 5
    with pytest.raises(RuntimeError):
        select([_r(1.0, fo=1)])


def test_default_on_needs_a_strict_dev_gain() -> None:
    assert not recommend_default_on({"accuracy": 0.9}, {"accuracy": 0.9})
    assert recommend_default_on({"accuracy": 0.9}, {"accuracy": 0.91})


def test_dev_word_report_uses_dev_pairs_only() -> None:
    split = load_split()
    held = set(split["heldout_words"])
    rows = dev_word_report()
    assert rows and all(r["pair"] in split["dev_pairs"] for r in rows)
    assert not [r for r in rows if r["word"] in held]


# --- Wiktionary calibration ------------------------------------------------------

from ops_copilot import wiktionary_calibration as wc  # noqa: E402

WART = Path(__file__).resolve().parents[1] / "artifacts" / "wiktionary_calibration.json"


def test_wiktionary_calibration_is_dev_only_and_covers_the_grid() -> None:
    art = json.loads(WART.read_text(encoding="utf-8"))
    splits = row_splits()
    assert art["calibration_rows"] == [rid for rid, _, _ in calibration_rows()]
    assert not [rid for rid in art["calibration_rows"] if splits.get(rid) == "heldout"]
    assert len(art["results"]) == len(wc.MIN_SCORES) * len(wc.MAX_NEIGHBOURS) * 2


def test_wiktionary_selection_prefers_the_strict_score() -> None:
    def r(acc, m, known=False, k=1, clean=1.0):
        return {
            "min_score": m, "known_words": known, "max_neighbours": k, "accuracy": acc,
            "clean_accuracy": clean, "n_fail_open": 0, "n_spurious_write": 0,
            "n_raw_pii_outputs": 0,
        }

    c = wc.select([r(0.9, 1), r(0.9, 2, known=True), r(0.9, 2, k=3), r(0.95, 1, clean=0.98)])
    assert (c["min_score"], c["known_words"], c["max_neighbours"]) == (2, False, 3)


def test_config_keeps_both_external_lexicons_off_without_a_dev_gain() -> None:
    from ops_copilot.config import CopilotConfig

    cfg = CopilotConfig()
    for path, flag in ((ART, cfg.use_tag_synonym_backoff), (WART, cfg.use_wiktionary_backoff)):
        art = json.loads(path.read_text(encoding="utf-8"))
        if not art["default_on"]:
            assert flag is False
