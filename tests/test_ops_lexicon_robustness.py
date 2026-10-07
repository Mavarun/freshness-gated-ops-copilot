"""Held-out result of the two external ops lexicons, pinned (both ship off).

Both settings were chosen on clean golden + dev synonym rows only, where
neither beat the backoff-off accuracy. Their first held-out run changed no
row at all (dev-chosen, together, and at their widest feasible setting), so
the defaults stay off. These tests pin that outcome so a future change to a
snapshot, an extract or the wiring shows up as a changed row.
"""

from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

import pytest

from ops_copilot import CopilotConfig
from ops_copilot.robustness import (
    OPS_LEXICON_ABLATIONS,
    OPS_LEXICON_CANDIDATE,
    TAGSYN_ON,
    WIKTIONARY_ON,
    _understood,
    changed_rows,
    run_robustness,
)

ART = Path(__file__).resolve().parents[1] / "artifacts"


@pytest.fixture(scope="module")
def report():
    return run_robustness()


@pytest.fixture(scope="module")
def both():
    return run_robustness(config=replace(CopilotConfig(), **OPS_LEXICON_ABLATIONS[OPS_LEXICON_CANDIDATE]))


def test_both_lexicons_ship_off() -> None:
    cfg = CopilotConfig()
    assert cfg.use_tag_synonym_backoff is False and cfg.use_wiktionary_backoff is False


def test_ablation_settings_are_the_dev_chosen_ones() -> None:
    tag = json.loads((ART / "tag_synonym_calibration.json").read_text(encoding="utf-8"))["chosen"]
    wik = json.loads((ART / "wiktionary_calibration.json").read_text(encoding="utf-8"))["chosen"]
    assert TAGSYN_ON["tag_synonym_sites"] == tag["sites"]
    assert TAGSYN_ON["tag_synonym_min_sites"] == tag["min_sites"]
    assert TAGSYN_ON["tag_synonym_max_neighbours"] == tag["max_neighbours"]
    assert TAGSYN_ON["tag_synonym_known_words"] == tag["known_words"]
    assert WIKTIONARY_ON["wiktionary_min_score"] == wik["min_score"]
    assert WIKTIONARY_ON["wiktionary_max_neighbours"] == wik["max_neighbours"]
    assert WIKTIONARY_ON["wiktionary_known_words"] == wik["known_words"]


def test_dev_chosen_lexicons_change_no_row(report, both) -> None:
    assert changed_rows(report, both) == []
    assert _understood(both) == _understood(report) == "1/12"
    assert both.clean_safety == {"n_fail_open": 0, "n_spurious_write": 0, "n_raw_pii_outputs": 0}


def test_committed_report_matches_the_pinned_outcome() -> None:
    m = json.loads((ART / "robustness_metrics.json").read_text(encoding="utf-8"))
    changes = m["ops_lexicon_changed_rows"]
    assert set(changes) == {k for k, v in OPS_LEXICON_ABLATIONS.items() if v}
    for label, rows in changes.items():
        if "word vectors" in label:
            # only the word vectors move rows: the PR #15 pair, unchanged
            assert {r["id"] for r in rows} == {"g21-synonym", "g39-synonym"}
        else:
            assert rows == [], label
    rows = m["ops_lexicon_ablations"]
    assert {r["heldout_answer_write_correct"] for r in rows.values()} == {"1/12"}
    assert all(r["n_fail_open"] == r["n_spurious_write"] == 0 for r in rows.values())
