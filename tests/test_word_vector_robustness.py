"""Held-out result of the counter-fitted backoff, pinned (it ships off).

The setting was chosen on clean golden + dev synonym rows only. Its first
held-out run fixed no held-out row and broke one (g21: NO_EVIDENCE ->
UNGROUNDED), so the default stays off; these tests pin that outcome so a
future change to the table or the wiring shows up as a changed row.
"""

from __future__ import annotations

from dataclasses import replace

import pytest

from ops_copilot import CopilotConfig
from ops_copilot.robustness import (
    WORDVEC_ON,
    _understood,
    changed_rows,
    leakage_report,
    run_robustness,
)


@pytest.fixture(scope="module")
def report():
    return run_robustness()


@pytest.fixture(scope="module")
def on():
    return run_robustness(config=replace(CopilotConfig(), **WORDVEC_ON))


def test_backoff_ships_off_by_default() -> None:
    assert CopilotConfig().use_word_vector_backoff is False


def test_calibrated_backoff_changes_exactly_two_rows(report, on) -> None:
    rows = {r["id"]: r for r in changed_rows(report, on)}
    assert set(rows) == {"g21-synonym", "g39-synonym"}
    assert rows["g39-synonym"]["split"] == "dev" and rows["g39-synonym"]["effect"] == "fixed"
    assert rows["g21-synonym"]["split"] == "heldout" and rows["g21-synonym"]["effect"] == "broke"
    assert rows["g21-synonym"]["after"] == "REFUSE_UNGROUNDED"


def test_backoff_on_is_safe_but_does_not_help_heldout(report, on) -> None:
    assert on.clean_accuracy == 1.0
    assert len(on.fail_open) == 0
    assert on.clean_safety == {"n_fail_open": 0, "n_spurious_write": 0, "n_raw_pii_outputs": 0}
    held_off = report.per_synonym_split["heldout"]["perturbed_accuracy"]
    held_on = on.per_synonym_split["heldout"]["perturbed_accuracy"]
    assert held_on == pytest.approx(held_off - 1 / 35)
    assert _understood(on) == _understood(report) == "1/12"
    assert on.perturbed_accuracy == pytest.approx(report.perturbed_accuracy)


def test_leakage_report_discloses_external_coverage() -> None:
    ext = leakage_report()["external_wordvec"]
    assert ext["heldout_words"] == 64 and ext["dev_words"] == 63
    assert 0 < ext["heldout_words_at_threshold"] <= ext["heldout_words_with_entry"]
    # authored lexicons stay free of held-out words
    leak = leakage_report()
    assert leak["heldout_words_in_map"] == [] and leak["heldout_words_in_glossary"] == []
