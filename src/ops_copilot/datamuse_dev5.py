"""Word-meaning-gated Datamuse on dev5 (pre-registered 2026-10-24, before any run on dev5).

Hypothesis (from PR #27, ``artifacts/datamuse_dev4_confirm.json``): the
unknown-words-only Datamuse arm gains on ops rewording (dev4 confirm 7 -> 10
of 21) but answers the must-refuse trap d4-37 because ``legal -> duty`` is a
collocation, not a synonym, and the corpus-context gate rewards it. Requiring
the counter-fitted vectors to agree that the unknown word can stand in for the
candidate (``datamuse_sense_min``, ``datamuse_pair_sense.py``) should remove
such wrong-sense mappings while keeping right-sense ones.

Disclosed before the grid was written: the counter-fitted cosine of the PR #27
post-hoc mappings was looked at (all dev4 words, a burned set): ``legal ->
duty`` 0.26, ``embargo -> freeze`` 0.29, ``itinerary -> schedule`` 0.21 (and
``-> path`` 0.77), ``overhaul -> maintenance`` 0.07, ``unspent -> remaining``
no cosine. So the gate is expected to cost right-sense fixes too, and the grid
floor 0.30 sits just above the trap. No dev5 row was scored by any config
before this file was committed.

Arms: every setting has ``use_datamuse_ml=True``, scope ``lone``,
``expand_known`` off, ``noun_only`` off.

Grid (``grid_settings``, 48): max_rank {20, 50, 100} x max_neighbours {1, 2} x
context_min {0, 2} x sense_min {0.30, 0.40, 0.50, 0.60}.

Calibration rows (``calibration_rows``): 15 dev + 43 dev2 + 45 dev3 + **all 44
dev4** (both halves burned, disclosed) + 24 dev5 ``tune`` = 171, plus the 51
clean golden rows. Held-out rows and the 20 dev5 ``confirm`` rows are never
scored here.

Safe: dev4's rule unchanged (``datamuse_dev4.is_safe_setting``): clean 1.000;
no fail-open, spurious write or raw PII; no new error against flag-off; no
must-refuse calibration row opens (d4-37 is now in calibration); the tests/
literal sweep opens no labelled trap.

Selection (``selection_key``): safe; calibration correct; calibration ANSWER
correct; **higher sense_min** (the stricter gate wins ties); lower rank; fewer
neighbours; higher context_min.

Candidate: safe and strictly above flag-off on calibration rows, else the flag
ships off and no confirm row is scored.

Confirm (one shot, ``confirm_decision``): ``datamuse_dev4.confirm_decision``
unchanged on the 20 dev5 confirm rows, the 203-row run and the sweep.
Recorded only, never used to decide: the dev4-chosen arm without the sense
gate on the same rows.
"""

from __future__ import annotations

from dataclasses import replace

from ops_copilot.config import CopilotConfig
from ops_copilot.datamuse_dev4 import confirm_decision as _dev4_confirm
from ops_copilot.datamuse_dev4 import is_safe_setting, off_config, opened_must_refuse
from ops_copilot.noun_gloss_sense_calibration import _clean_stats
from ops_copilot.paraphrase_set import load_paraphrase_set
from ops_copilot.safety_sweep import sweep
from ops_copilot.synonym_dev2 import load_dev2
from ops_copilot.synonym_dev3 import load_dev3
from ops_copilot.synonym_dev4 import load_dev4
from ops_copilot.synonym_dev5 import half
from ops_copilot.synonym_split import load_split
from ops_copilot.wordnet_dev2 import fixed_rows, is_safe, new_errors, score_rows

GRID_MAX_RANK = (20, 50, 100)
GRID_NEIGHBOURS = (1, 2)
GRID_CONTEXT = (0, 2)
GRID_SENSE = (0.30, 0.40, 0.50, 0.60)
# The dev4-chosen arm (no sense gate), scored on dev5 confirm for the record only.
DEV4_CHOSEN = {"max_rank": 100, "max_neighbours": 2, "context_min": 2, "sense_min": 0.0}

__all__ = ["off_config", "is_safe_setting", "opened_must_refuse"]


def grid_settings() -> list[dict]:
    return [
        {"max_rank": r, "max_neighbours": n, "context_min": k, "sense_min": t}
        for r in GRID_MAX_RANK
        for n in GRID_NEIGHBOURS
        for k in GRID_CONTEXT
        for t in GRID_SENSE
    ]


def config_for(setting: dict, base: CopilotConfig | None = None) -> CopilotConfig:
    return replace(
        base or CopilotConfig(),
        use_datamuse_ml=True,
        datamuse_scope="lone",
        datamuse_max_rank=setting["max_rank"],
        datamuse_max_neighbours=setting["max_neighbours"],
        datamuse_noun_only=False,
        datamuse_context_min=setting["context_min"],
        datamuse_expand_known=False,
        datamuse_sense_min=setting["sense_min"],
    )


def calibration_rows() -> list[dict]:
    split = load_split()
    dev = [
        {"id": r["id"], "query": r["query"], "expect_decision": r["expect_decision"], "set": "dev"}
        for r in load_paraphrase_set()
        if r["perturbation"] == "synonym" and split["rows"][r["id"]]["split"] == "dev"
    ]
    d2 = [{**r, "set": "dev2"} for r in load_dev2()]
    d3 = [{**r, "set": "dev3"} for r in load_dev3()]
    d4 = [{**r, "set": "dev4"} for r in load_dev4()]
    d5 = [{**r, "set": "dev5_tune"} for r in half("tune")]
    return dev + d2 + d3 + d4 + d5


def selection_key(r: dict) -> tuple:
    return (
        -int(r["safe"]),
        -r["calib_correct"],
        -r["calib_answer_correct"],
        -r["sense_min"],
        r["max_rank"],
        r["max_neighbours"],
        -r["context_min"],
    )


def _public(stats: dict) -> dict:
    return {k: v for k, v in stats.items() if k not in ("ok", "decisions")}


def calibrate(settings: list[dict] | None = None, rows: list[dict] | None = None) -> dict:
    rows = calibration_rows() if rows is None else rows
    off_cfg = off_config()
    off = score_rows(off_cfg, rows)
    off_opened = set(opened_must_refuse(off, rows))
    results = []
    for st in settings or grid_settings():
        cfg = config_for(st)
        clean = _clean_stats(cfg)
        on = score_rows(cfg, rows)
        opened = [r for r in opened_must_refuse(on, rows) if r not in off_opened]
        sw = sweep(cfg)
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
                "must_refuse_opened": opened,
                "sweep_n_opened": sw["n_opened"],
                "sweep_labelled_trap_opened": [c["query"] for c in sw["labelled_trap_opened"]],
                "safe": is_safe_setting(is_safe(clean, off, on), opened, sw),
            }
        )
    results.sort(key=selection_key)
    chosen = results[0]
    sets = ("dev", "dev2", "dev3", "dev4", "dev5_tune")
    return {
        "n_rows": len(rows),
        "rows_by_set": {s: sum(r.get("set") == s for r in rows) for s in sets},
        "n_settings": len(results),
        "baseline_off": {**_public(off), "clean": _clean_stats(off_cfg)},
        "chosen": chosen,
        "n_safe": sum(r["safe"] for r in results),
        "candidate": bool(chosen["safe"] and chosen["calib_correct"] > off["correct"]),
        "results": results,
    }


def confirm_decision(off_confirm: dict, on_confirm: dict, off_rob: dict, on_rob: dict,
                     confirm_rows: list[dict], sweep_report: dict) -> dict:
    return _dev4_confirm(off_confirm, on_confirm, off_rob, on_rob, confirm_rows, sweep_report)
