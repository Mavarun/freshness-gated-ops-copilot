"""Context-gated Datamuse on dev3 (pre-registered 2026-10-21, before any run on dev3).

Question: does the corpus-context gate (``datamuse_context_min``) fix the
precision problem the 2026-10-20 diagnostic found (noisy neighbours first,
``plan -> chart``), so a wider rank cut-off can reach linked-but-gated swaps
without new errors? And does the shelved dev2-chosen arm hold up on a fresh
confirm set? This module fixes everything before any config sees a dev3 row.

Calibration rows (``calibration_rows``): dev synonym rows of the 203-row set
(15) + **all 43 dev2 rows** + the dev3 ``calib`` half (25), plus the 51 clean
golden rows for the safety check. dev2's confirm half joins calibration
because it has been scored twice and is no longer a confirm set; that is
disclosed, not hidden. Held-out rows and the dev3 ``confirm`` half are never
scored here.

Grid (``grid_settings``, 48 settings): scope {known, lone} x max_rank
{10, 20, 50, 100} x max_neighbours {1, 2} x context_min {0, 1, 2};
noun_only stays off (its config default). ``all`` scope is left out: every
all-scope setting was unsafe on dev2, and the gate needs a query context the
retrieval rewrite does not have. context_min 0 with lone / 10 / 2 is the
shelved dev2-chosen arm, so it competes on the same rows.

Safe: ``wordnet_dev2.is_safe`` (clean 1.000; zero fail-open, spurious write,
raw PII; no new error against flag-off on any calibration row).

Selection (``selection_key``): safe; calibration rows correct; calibration
ANSWER rows correct; narrower scope; fewest knobs off their config defaults
(rank 10, one neighbour, context 0); then the more restrictive value (lower
rank, fewer neighbours, *higher* context_min).

Candidate: safe and strictly above flag-off on calibration rows, else the
flag ships off and no confirm row is scored.

Confirm (one shot, ``wordnet_dev2.confirm_decision``, unchanged) on the 20
dev3 confirm rows plus the 203-row robustness run (held-out as no-harm only).
Recorded but never used to choose: the dev2-chosen WordNet and Datamuse arms
on the same confirm rows, and every arm on the fresh everyday set.
"""

from __future__ import annotations

from dataclasses import replace

from ops_copilot.config import CopilotConfig
from ops_copilot.noun_gloss_sense_calibration import _clean_stats
from ops_copilot.paraphrase_set import load_paraphrase_set
from ops_copilot.synonym_dev2 import load_dev2
from ops_copilot.synonym_dev3 import half
from ops_copilot.synonym_split import load_split
from ops_copilot.wordnet_dev2 import fixed_rows, is_safe, new_errors, score_rows

GRID_SCOPES = ("known", "lone")
GRID_MAX_RANK = (10, 20, 50, 100)
GRID_NEIGHBOURS = (1, 2)
GRID_CONTEXT = (0, 1, 2)
SCOPE_RANK = {"known": 0, "lone": 1}
_D = CopilotConfig()
DEFAULTS = {
    "max_rank": _D.datamuse_max_rank,
    "max_neighbours": _D.datamuse_max_neighbours,
    "context_min": _D.datamuse_context_min,
}


def grid_settings() -> list[dict]:
    return [
        {"scope": s, "max_rank": r, "max_neighbours": n, "context_min": k}
        for s in GRID_SCOPES
        for r in GRID_MAX_RANK
        for n in GRID_NEIGHBOURS
        for k in GRID_CONTEXT
    ]


def config_for(setting: dict, base: CopilotConfig | None = None) -> CopilotConfig:
    return replace(
        base or CopilotConfig(),
        use_datamuse_ml=True,
        datamuse_scope=setting["scope"],
        datamuse_max_rank=setting["max_rank"],
        datamuse_max_neighbours=setting["max_neighbours"],
        datamuse_noun_only=False,
        datamuse_context_min=setting["context_min"],
    )


def calibration_rows() -> list[dict]:
    split = load_split()
    dev = [
        {"id": r["id"], "query": r["query"], "expect_decision": r["expect_decision"], "set": "dev"}
        for r in load_paraphrase_set()
        if r["perturbation"] == "synonym" and split["rows"][r["id"]]["split"] == "dev"
    ]
    d2 = [{**r, "set": "dev2"} for r in load_dev2()]
    d3 = [{**r, "set": "dev3_calib"} for r in half("calib")]
    return dev + d2 + d3


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
        -r["context_min"],
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
        "rows_by_set": {s: sum(r.get("set") == s for r in rows) for s in ("dev", "dev2", "dev3_calib")},
        "n_settings": len(results),
        "baseline_off": {**_public(off), "clean": _clean_stats(off_cfg)},
        "chosen": chosen,
        "n_safe": sum(r["safe"] for r in results),
        "candidate": bool(chosen["safe"] and chosen["calib_correct"] > off["correct"]),
        "results": results,
    }
