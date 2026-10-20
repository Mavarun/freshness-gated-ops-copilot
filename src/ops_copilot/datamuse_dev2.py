"""Datamuse means-like gate on dev2 (pre-registered 2026-10-20, before any run).

The 2026-10-19 coverage diagnostic said the next word source must cover
*usage* synonymy (``delay~latency``, ``load~utilization``), which WordNet's
noun graph does not hold. This module fixes the protocol for the Datamuse
``ml`` backoff (``datamuse_senses.py``) before any config is run on dev2 rows.

Calibration rows: clean golden (51) + dev synonym rows (15) + dev2 ``calib``
half (22), the same rows as ``wordnet_dev2.calibration_rows``. Held-out rows
and the dev2 ``confirm`` half are never scored here.

Grid (``grid_settings``, 60 settings): scope {known, lone, all} x max_rank
{3, 5, 10, 20, 50} x max_neighbours {1, 2} x noun_only {off, on}. Datamuse is
the only noun backoff on (WordNet and the Wiktionary noun gloss stay at their
shipped off defaults).

Safe (``wordnet_dev2.is_safe``): clean 1.000; zero fail-open and zero
spurious PROPOSE_WRITE on every calibration row; zero raw PII; no new error
against flag-off on any calibration row.

Selection (``selection_key``): safe first; then calibration rows correct;
then calibration ANSWER rows correct; then the narrowest scope (known < lone
< all); then **the fewest knobs moved off their config defaults** (max_rank
10, max_neighbours 1, noun_only off); only then the most restrictive value.
That middle step is the fix the 2026-10-19 slice recorded: tied settings
behave identically on every calibration row, so a knob the calibration rows
never exercise stays at its default instead of being pushed to its most
restrictive value (which cost recall on confirm rows last time).

Candidate: the chosen setting must be safe and strictly beat flag-off on
calibration rows; otherwise the flag ships off and no confirm row is scored.

Confirm (one shot): ``wordnet_dev2.confirm_decision``, unchanged: dev2
confirm accuracy strictly up, confirm ANSWER not down, no new error, zero
fail-open / spurious write / raw PII; clean 1.000 and zero fail-open /
spurious write / raw PII on the 203-row robustness run; held-out accuracy and
held-out ANSWER rows not down. Held-out is a no-harm check only. This is the
second scored use of the dev2 confirm half (the first was the WordNet arm on
2026-10-19, which changed no confirm row).
"""

from __future__ import annotations

from dataclasses import replace

from ops_copilot.config import CopilotConfig
from ops_copilot.noun_gloss_sense_calibration import _clean_stats
from ops_copilot.wordnet_dev2 import (
    calibration_rows,
    fixed_rows,
    is_safe,
    new_errors,
    score_rows,
)

GRID_SCOPES = ("known", "lone", "all")
GRID_MAX_RANK = (3, 5, 10, 20, 50)
GRID_NEIGHBOURS = (1, 2)
GRID_NOUN_ONLY = (False, True)
SCOPE_RANK = {"known": 0, "lone": 1, "all": 2}
_DEFAULTS = CopilotConfig()
DEFAULTS = {
    "max_rank": _DEFAULTS.datamuse_max_rank,
    "max_neighbours": _DEFAULTS.datamuse_max_neighbours,
    "noun_only": _DEFAULTS.datamuse_noun_only,
}


def grid_settings() -> list[dict]:
    return [
        {"scope": scope, "max_rank": rank, "max_neighbours": n, "noun_only": noun}
        for scope in GRID_SCOPES
        for rank in GRID_MAX_RANK
        for n in GRID_NEIGHBOURS
        for noun in GRID_NOUN_ONLY
    ]


def config_for(setting: dict, base: CopilotConfig | None = None) -> CopilotConfig:
    return replace(
        base or CopilotConfig(),
        use_datamuse_ml=True,
        datamuse_scope=setting["scope"],
        datamuse_max_rank=setting["max_rank"],
        datamuse_max_neighbours=setting["max_neighbours"],
        datamuse_noun_only=setting["noun_only"],
    )


def knobs_off_default(setting: dict) -> int:
    return sum(setting[k] != v for k, v in DEFAULTS.items())


def selection_key(r: dict) -> tuple:
    return (
        -int(r["safe"]),
        -r["calib_correct"],
        -r["calib_answer_correct"],
        SCOPE_RANK[r["scope"]],
        knobs_off_default(r),
        r["max_rank"],
        r["max_neighbours"],
        -int(r["noun_only"]),  # noun-only is the more restrictive value
    )


def _public(stats: dict) -> dict:
    return {k: v for k, v in stats.items() if k != "ok"}


def calibrate(settings: list[dict] | None = None, rows: list[dict] | None = None) -> dict:
    rows = calibration_rows() if rows is None else rows
    off_cfg = CopilotConfig(use_datamuse_ml=False)
    off = score_rows(off_cfg, rows)
    results = []
    for st in settings or grid_settings():
        cfg = config_for(st)
        clean = _clean_stats(cfg)
        on = score_rows(cfg, rows)
        results.append(
            {
                **st,
                "clean_accuracy": clean["clean_accuracy"],
                "calib_correct": on["correct"],
                "calib_accuracy": on["accuracy"],
                "calib_answer_correct": on["answer_correct"],
                "n_fail_open": on["n_fail_open"] + clean["n_fail_open"],
                "n_spurious_write": on["n_spurious_write"] + clean["n_spurious_write"],
                "n_raw_pii": on["n_raw_pii"],
                "fixed": fixed_rows(off, on),
                "new_errors": new_errors(off, on),
                "safe": is_safe(clean, off, on),
            }
        )
    results.sort(key=selection_key)
    chosen = results[0]
    return {
        "n_rows": len(rows),
        "n_settings": len(results),
        "baseline_off": {**_public(off), "clean": _clean_stats(off_cfg)},
        "chosen": chosen,
        "n_safe": sum(r["safe"] for r in results),
        "candidate": bool(chosen["safe"] and chosen["calib_correct"] > off["correct"]),
        "results": results,
    }
