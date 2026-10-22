"""Unknown-words-only Datamuse on dev4 (pre-registered 2026-10-22, before any run on dev4).

Hypothesis (from the post-hoc 2026-10-21 run, ``artifacts/datamuse_dev3_posthoc.json``):
giving Datamuse alternatives **only to words the corpus does not know**
(``datamuse_expand_known=False``) keeps the context-gated backoff's gains on
ops rewording without the fail-open that expanding a known word caused
(``revert -> returning`` opening the toggle trap in ``tests/test_synonyms.py``).
dev3 cannot test it: its confirm half has been scored by this family twice.

Arms: every setting has ``use_datamuse_ml=True``, scope ``lone`` (the only
scope that maps unknown words; ``known`` with ``expand_known=False`` maps
nothing), ``noun_only`` off and ``expand_known=False``.

Grid (``grid_settings``, 24): max_rank {10, 20, 50, 100} x max_neighbours
{1, 2} x context_min {0, 1, 2}. The post-hoc arm (50 / 2 / 2) is inside.

Calibration rows (``calibration_rows``): dev synonym rows of the 203-row set
(15) + all 43 dev2 rows + **all 45 dev3 rows** (both halves are burned for this
family, disclosed) + the 23 dev4 ``tune`` rows = 126, plus the 51 clean golden
rows. Held-out rows and the 21 dev4 ``confirm`` rows are never scored here.

Safe (``is_safe_setting``), all before any confirm row is scored (the dev3
weakness: the unit-test sweep ran only after the confirm):

1. ``wordnet_dev2.is_safe``: clean 1.000; zero fail-open, spurious write, raw
   PII; no new error against flag-off on any calibration row;
2. **must-refuse**: no calibration row whose label is a refusal comes back
   ANSWER / PROPOSE_WRITE (``opened_must_refuse``);
3. **unit-test sweep** (``safety_sweep.sweep``): no labelled trap opens.

Selection (``selection_key``): safe; calibration correct; calibration ANSWER
correct; fewest knobs off the frozen defaults (rank 10, one neighbour,
context 0); then lower rank, fewer neighbours, higher context_min.

Candidate: safe and strictly above flag-off on calibration rows, else the flag
ships off and no confirm row is scored.

Confirm (one shot, ``confirm_decision``): ``wordnet_dev2.confirm_decision``
unchanged (confirm gain, ANSWER not down, no new error, no fail-open / write /
PII, clean 1.000, robustness clean, held-out accuracy and ANSWER not down) on
the 21 dev4 confirm rows and the 203-row run, **plus** two no-new-error checks:
no dev4 confirm must-refuse row opens, and the sweep still opens no labelled
trap. ``default_on`` only if every check passes.
"""

from __future__ import annotations

from dataclasses import replace

from ops_copilot.config import CopilotConfig
from ops_copilot.noun_gloss_sense_calibration import _clean_stats
from ops_copilot.paraphrase_set import load_paraphrase_set
from ops_copilot.safety_sweep import sweep
from ops_copilot.synonym_dev2 import load_dev2
from ops_copilot.synonym_dev3 import load_dev3
from ops_copilot.synonym_dev4 import OPENING, half
from ops_copilot.synonym_split import load_split
from ops_copilot.wordnet_dev2 import confirm_decision as _base_confirm
from ops_copilot.wordnet_dev2 import fixed_rows, is_safe, new_errors, score_rows

GRID_MAX_RANK = (10, 20, 50, 100)
GRID_NEIGHBOURS = (1, 2)
GRID_CONTEXT = (0, 1, 2)
# Frozen literals as registered on 2026-10-22 (see datamuse_dev3.DEFAULTS).
DEFAULTS = {"max_rank": 10, "max_neighbours": 1, "context_min": 0}


def grid_settings() -> list[dict]:
    return [
        {"max_rank": r, "max_neighbours": n, "context_min": k}
        for r in GRID_MAX_RANK
        for n in GRID_NEIGHBOURS
        for k in GRID_CONTEXT
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
    )


def off_config() -> CopilotConfig:
    return replace(CopilotConfig(), use_datamuse_ml=False)


def calibration_rows() -> list[dict]:
    split = load_split()
    dev = [
        {"id": r["id"], "query": r["query"], "expect_decision": r["expect_decision"], "set": "dev"}
        for r in load_paraphrase_set()
        if r["perturbation"] == "synonym" and split["rows"][r["id"]]["split"] == "dev"
    ]
    d2 = [{**r, "set": "dev2"} for r in load_dev2()]
    d3 = [{**r, "set": "dev3"} for r in load_dev3()]
    d4 = [{**r, "set": "dev4_tune"} for r in half("tune")]
    return dev + d2 + d3 + d4


def opened_must_refuse(stats: dict, rows: list[dict]) -> list[str]:
    """Ids of rows labelled as a refusal that the scored config answered / wrote."""
    by_id = {r["id"]: r["expect_decision"] for r in rows}
    return sorted(rid for rid, dec in stats["decisions"].items()
                  if by_id.get(rid) not in OPENING and dec in OPENING)


def knobs_off_default(setting: dict) -> int:
    return sum(setting[k] != v for k, v in DEFAULTS.items())


def selection_key(r: dict) -> tuple:
    return (
        -int(r["safe"]),
        -r["calib_correct"],
        -r["calib_answer_correct"],
        knobs_off_default(r),
        r["max_rank"],
        r["max_neighbours"],
        -r["context_min"],
    )


def is_safe_setting(base_safe: bool, must_refuse_opened: list[str], sweep_report: dict) -> bool:
    return bool(base_safe and not must_refuse_opened and sweep_report["safe"])


def _public(stats: dict) -> dict:
    return {k: v for k, v in stats.items() if k not in ("ok", "decisions")}


def calibrate(settings: list[dict] | None = None, rows: list[dict] | None = None) -> dict:
    rows = calibration_rows() if rows is None else rows
    off_cfg = off_config()
    off = score_rows(off_cfg, rows)
    results = []
    for st in settings or grid_settings():
        cfg = config_for(st)
        clean = _clean_stats(cfg)
        on = score_rows(cfg, rows)
        opened = [r for r in opened_must_refuse(on, rows) if r not in opened_must_refuse(off, rows)]
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
    return {
        "n_rows": len(rows),
        "rows_by_set": {s: sum(r.get("set") == s for r in rows) for s in ("dev", "dev2", "dev3", "dev4_tune")},
        "n_settings": len(results),
        "baseline_off": {**_public(off), "clean": _clean_stats(off_cfg)},
        "chosen": chosen,
        "n_safe": sum(r["safe"] for r in results),
        "candidate": bool(chosen["safe"] and chosen["calib_correct"] > off["correct"]),
        "results": results,
    }


def confirm_decision(off_confirm: dict, on_confirm: dict, off_rob: dict, on_rob: dict,
                     confirm_rows: list[dict], sweep_report: dict) -> dict:
    base = _base_confirm(off_confirm, on_confirm, off_rob, on_rob)
    newly = [r for r in opened_must_refuse(on_confirm, confirm_rows)
             if r not in opened_must_refuse(off_confirm, confirm_rows)]
    checks = {
        **base["checks"],
        "confirm_must_refuse_held": not newly,
        "sweep_no_labelled_trap": bool(sweep_report["safe"]),
    }
    return {"checks": checks, "default_on": all(checks.values()), "must_refuse_opened": newly}
