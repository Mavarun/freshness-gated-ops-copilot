"""First held-out run of the dev-chosen passage classifier, pinned.

The setting was chosen on clean golden + dev synonym rows only and committed
before this run. Held-out accuracy 0.429 -> 0.457 (one REFUSE_DISAGREE row),
held-out answers / writes still 1 of 12, no fail-open, spurious write or raw
PII. On the fresh general-English set (written before the model existed, so
blind for it) 7/26 -> 18/26 with 0 fail-open. The pre-registered go / no-go
rule is met.
"""

from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

import pytest

from ops_copilot import CopilotConfig
from ops_copilot.robustness import (
    PASSAGE_SUPPORT_ABLATIONS,
    PASSAGE_SUPPORT_CANDIDATE,
    PASSAGE_SUPPORT_ON,
    _understood,
    changed_rows,
    run_robustness,
)

METRICS = Path(__file__).resolve().parents[1] / "artifacts" / "robustness_metrics.json"
OFF = {"use_passage_support_model": False}


@pytest.fixture(scope="module")
def off():
    return run_robustness(config=replace(CopilotConfig(), **OFF))


@pytest.fixture(scope="module")
def on():
    return run_robustness(config=replace(CopilotConfig(), **PASSAGE_SUPPORT_ON))


def test_candidate_is_the_dev_chosen_setting() -> None:
    assert PASSAGE_SUPPORT_ABLATIONS[PASSAGE_SUPPORT_CANDIDATE] == PASSAGE_SUPPORT_ON
    cal = json.loads((METRICS.parent / "passage_support_calibration.json").read_text())["chosen"]
    cfg = CopilotConfig()
    assert (cfg.passage_support_min_prob, cfg.passage_support_strict, cfg.passage_support_known_words,
            cfg.passage_support_max_terms) == (cal["min_prob"], cal["strict"], cal["known_words"], cal["max_terms"])


def test_changed_rows_are_fixes_only(off, on) -> None:
    rows = {r["id"]: r for r in changed_rows(off, on)}
    assert set(rows) == {"g24-synonym", "g28-synonym", "g35-synonym", "g39-synonym", "g48-synonym"}
    assert all(r["effect"] == "fixed" for r in rows.values())
    assert [i for i, r in rows.items() if r["split"] == "heldout"] == ["g28-synonym"]


def test_heldout_gain_is_one_row_and_safe(off, on) -> None:
    assert on.clean_accuracy == 1.0
    assert len(on.fail_open) == 0
    assert on.clean_safety == {"n_fail_open": 0, "n_spurious_write": 0, "n_raw_pii_outputs": 0}
    assert off.per_synonym_split["heldout"]["perturbed_accuracy"] == pytest.approx(15 / 35)
    assert on.per_synonym_split["heldout"]["perturbed_accuracy"] == pytest.approx(16 / 35)
    assert on.per_synonym_split["dev"]["perturbed_accuracy"] == pytest.approx(14 / 15)
    assert _understood(on) == _understood(off) == "1/12"
    assert on.perturbed_accuracy == pytest.approx(off.perturbed_accuracy + 5 / 203)


def test_artifact_records_the_first_heldout_run() -> None:
    m = json.loads(METRICS.read_text(encoding="utf-8"))
    rows = m["passage_support_ablations"]
    cand, base = rows[PASSAGE_SUPPORT_CANDIDATE], rows["default (passage classifier off)"]
    assert cand["synonym_heldout"] > base["synonym_heldout"]
    assert cand["heldout_answer_write_correct"] == "1/12"
    assert cand["n_fail_open"] == cand["n_spurious_write"] == cand["n_raw_pii_outputs"] == 0
    assert cand["clean_safety"] == {"n_fail_open": 0, "n_spurious_write": 0, "n_raw_pii_outputs": 0}


def test_fresh_set_blind_run() -> None:
    from ops_copilot.fresh_synonym_eval import CONFIGS, load_fresh, score

    rows = load_fresh()
    base = replace(CopilotConfig(), use_word_vector_backoff=False, **OFF)
    off = score(base, rows)
    on = score(replace(base, **CONFIGS["+ passage classifier (dev-chosen)"]), rows)
    assert off["n"] - len(off["wrong"]) == 7 and on["n"] - len(on["wrong"]) == 18
    assert on["n_fail_open"] == 0 and on["n_spurious_write"] == 0
    broke = {w.split(":")[0] for w in on["wrong"]} - {w.split(":")[0] for w in off["wrong"]}
    assert broke == set()
