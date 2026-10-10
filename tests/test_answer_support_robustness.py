"""Held-out result of the answer-support model, pinned (it ships off).

The setting was chosen on clean golden + dev synonym rows only. Its first
held-out run changed no held-out row (0.429, 1 of 12 understood, as before);
its only change is the dev row it was calibrated on (g48). It passes the
pre-registered no-harm bar but brings no held-out gain, so it stays opt-in.
These tests pin that outcome so a change to the table or the wiring shows up.
"""

from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

import pytest

from ops_copilot import CopilotConfig
from ops_copilot.robustness import (
    ANSWER_SUPPORT_ABLATIONS,
    ANSWER_SUPPORT_CANDIDATE,
    ANSWER_SUPPORT_ON,
    _understood,
    changed_rows,
    run_robustness,
)

# Measured before the passage classifier was switched on (2026-10-10).
PRE_PASSAGE = replace(CopilotConfig(), use_passage_support_model=False)
METRICS = Path(__file__).resolve().parents[1] / "artifacts" / "robustness_metrics.json"


@pytest.fixture(scope="module")
def report():
    return run_robustness(config=PRE_PASSAGE)


@pytest.fixture(scope="module")
def on():
    return run_robustness(config=replace(PRE_PASSAGE, **ANSWER_SUPPORT_ON))


def test_model_ships_off_by_default() -> None:
    assert CopilotConfig().use_answer_support_model is False
    assert ANSWER_SUPPORT_ABLATIONS[ANSWER_SUPPORT_CANDIDATE] == ANSWER_SUPPORT_ON


def test_dev_chosen_model_changes_only_the_dev_row_it_was_tuned_on(report, on) -> None:
    rows = {r["id"]: r for r in changed_rows(report, on)}
    assert set(rows) == {"g48-synonym"}
    assert rows["g48-synonym"]["split"] == "dev" and rows["g48-synonym"]["effect"] == "fixed"
    assert rows["g48-synonym"]["after"] == "REFUSE_PII"


def test_model_on_is_safe_and_neutral_on_heldout(report, on) -> None:
    assert on.clean_accuracy == 1.0
    assert len(on.fail_open) == 0
    assert on.clean_safety == {"n_fail_open": 0, "n_spurious_write": 0, "n_raw_pii_outputs": 0}
    held_off = report.per_synonym_split["heldout"]["perturbed_accuracy"]
    held_on = on.per_synonym_split["heldout"]["perturbed_accuracy"]
    assert held_on == pytest.approx(held_off) == pytest.approx(15 / 35)
    assert _understood(on) == _understood(report) == "1/12"
    assert on.perturbed_accuracy == pytest.approx(report.perturbed_accuracy + 1 / 203)


def test_artifact_records_the_first_heldout_run() -> None:
    m = json.loads(METRICS.read_text(encoding="utf-8"))
    rows = m["answer_support_ablations"]
    cand = rows[ANSWER_SUPPORT_CANDIDATE]
    base = rows["default (answer-support model off)"]
    assert cand["synonym_heldout"] == base["synonym_heldout"]
    assert cand["heldout_answer_write_correct"] == "1/12"
    assert [r["id"] for r in m["answer_support_changed_rows"][ANSWER_SUPPORT_CANDIDATE]] == ["g48-synonym"]


def test_fresh_set_blind_run_fixes_one_row_and_opens_nothing() -> None:
    from ops_copilot.fresh_synonym_eval import CONFIGS, load_fresh, score

    rows = load_fresh()
    base = replace(PRE_PASSAGE, use_word_vector_backoff=False)
    off = score(base, rows)
    on = score(replace(base, **CONFIGS["+ answer-support model (dev-chosen)"]), rows)
    assert off["n"] - len(off["wrong"]) == 7 and on["n"] - len(on["wrong"]) == 8
    fixed = {w.split(":")[0] for w in off["wrong"]} - {w.split(":")[0] for w in on["wrong"]}
    assert fixed == {"f03"}
    assert on["n_fail_open"] == 0 and on["n_spurious_write"] == 0
    # right outcome through a topical pair, not the replaced word (primary)
    from ops_copilot import Copilot

    f03 = next(r for r in rows if r["id"] == "f03")
    res = Copilot(config=replace(base, **CONFIGS["+ answer-support model (dev-chosen)"])).ask(f03["query"])
    assert res.grounding.translation_rescued == ["principal<-owner"]


def test_leakage_report_discloses_answer_support_coverage() -> None:
    from ops_copilot.robustness import leakage_report

    ans = leakage_report()["external_answer_support"]
    assert ans["threshold"] == CopilotConfig().answer_support_min_score
    assert ans["heldout"]["words"] == 64
    # computed after the decision: no held-out key word clears the threshold
    assert ans["heldout"]["key_at_threshold"] == 0
    # the nearest miss is a near-spelling, not a sense: configuration <- config 4.24
    assert "configuration<-config 4.24" in ans["heldout"]["key_hits"]
    # the report lists the key-word hits next to the count they belong to
    lines = (METRICS.parent / "robustness_report.md").read_text().splitlines()
    held = next(x for x in lines if x.startswith("- answer-support model, heldout"))
    assert "at any stored lift 5 (address<-email 2.20," in held
