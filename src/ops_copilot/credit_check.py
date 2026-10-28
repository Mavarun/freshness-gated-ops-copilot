"""Credited-word check: protocol (pre-registered 2026-10-28, before any run on traps v3 or dev7).

Question (README weakness, 2026-10-27): the shipped null test answers the fresh
trap at2-01 (``What taste is the LaunchDarkly checkout_retry flag?``) and no
percentile cut separates traps from real paraphrases, because the traps are
credited by generic passage words (``taste <- one``). Can a check on the
*credited word* (``passage_support.credited_word_problems``) close the traps
without costing real paraphrases?

Disclosed before this file: on the spent rows of ``artifacts/passage_null_overlap.md``
the three signals were looked at by hand. Stop words catch ``one``, ``two``,
``other``, ``only`` but not ``region``, ``adds``, ``percent``, ``bot``;
frequency rank catches ``one`` (3), ``only`` (7), ``other`` (8), ``default``
(43), ``two`` (60) but also ``time`` (18, credited for a keep row); the
neighbour rank does **not** separate: ``plan <- schedule`` (a real
substitute) ranks 1,392, worse than ``taste <- one`` (547). Each knob was also
run once on the spent at2-01 to test the mechanism (``tests/test_credited_word_check.py``:
all three refuse it). No row of ``attribute_traps_v3.jsonl`` or ``synonym_dev7.jsonl``
has been scored by any config.

Arms (``grid_settings``, 31): on top of the shipped default (null test, seed 42,
q = 0.30, sticky), ``stop`` in {off, on} x ``top_freq`` in {0, 50, 100, 200} x
``max_rank`` in {0, 500, 1000, 2000}, minus all-off. Baseline: the shipped default.

Calibration rows: the 171 rows of ``datamuse_dev5.calibration_rows``, all 45
(spent) dev6 rows and the 22 dev7 ``tune`` rows (238), the 51 clean golden
rows, and 95 traps: all 36 v1, all 40 v2 (both spent) and the 19 v3 ``tune`` traps.

Safe (``is_safe_setting``): clean 1.000 with no fail-open or spurious write; no
spurious write or raw PII on calibration rows; no must-refuse calibration row
opens; **no calibration trap opens (so at2-01 must close)**; the tests/
literal sweep opens no labelled trap; cost vs the shipped default at most
``MAX_ROWS_LOST`` (6) calibration rows and ``MAX_ANSWER_LOST`` (3) ANSWER rows.

Selection (``selection_key``): safe; most calibration rows correct; most ANSWER
rows correct; fewest active checks; then the looser setting (stop off before
on, smaller ``top_freq``, larger ``max_rank``; 0 = off counts as loosest). No safe
setting: the check ships off and no confirm row is scored.

One-shot confirm (``confirm_decision``), on rows never seen while designing:

- the 19 v3 ``confirm`` traps: the chosen arm opens none;
- the 18 dev7 ``confirm`` rows: **no new error** against the shipped default
  and no must-refuse row opens (the no-new-error rule);
- 203-row robustness run: clean 1.000; no fail-open, spurious write or raw PII;
  held-out accuracy and held-out ANSWER not below the shipped default; overall
  perturbed accuracy within 2 rows of it;
- the sweep opens no labelled trap.

Recorded only, never used to decide: the shipped default on the same rows, an
exact sign test on changed dev7 confirm rows, and the fresh general-English set.

If every check passes, the default becomes the chosen arm, the strict ``xfail``
on at2-01 is removed and every report-only artifact is re-pinned with its cost;
otherwise the knobs stay off and traps v3 confirm and dev7 confirm are spent.
"""

from __future__ import annotations

from dataclasses import replace
from itertools import product

from ops_copilot.attribute_traps import load_traps, score_traps
from ops_copilot.attribute_traps_v2 import load_traps_v2
from ops_copilot.attribute_traps_v3 import half_v3
from ops_copilot.config import CopilotConfig
from ops_copilot.datamuse_dev4 import opened_must_refuse
from ops_copilot.datamuse_dev5 import calibration_rows as _dev5_calibration_rows
from ops_copilot.noun_gloss_sense_calibration import _clean_stats
from ops_copilot.safety_sweep import sweep
from ops_copilot.synonym_dev6 import load_dev6
from ops_copilot.synonym_dev7 import half as dev7_half
from ops_copilot.wordnet_dev2 import fixed_rows, new_errors, score_rows

GRID_STOP = (False, True)
GRID_TOP_FREQ = (0, 50, 100, 200)
GRID_MAX_RANK = (0, 500, 1000, 2000)
MAX_ROWS_LOST = 6
MAX_ANSWER_LOST = 3
PERTURBED_ROWS_TOLERANCE = 2


def shipped_config() -> CopilotConfig:
    """The shipped default before this slice: every baseline here."""
    return replace(CopilotConfig(), passage_support_credit_stop=False, passage_support_credit_top_freq=0,
                   passage_support_credit_max_rank=0)


def grid_settings() -> list[dict]:
    return [{"stop": s, "top_freq": f, "max_rank": r}
            for s, f, r in product(GRID_STOP, GRID_TOP_FREQ, GRID_MAX_RANK) if s or f or r]


def config_for(setting: dict, base: CopilotConfig | None = None) -> CopilotConfig:
    return replace(base or shipped_config(), passage_support_credit_stop=bool(setting["stop"]),
                   passage_support_credit_top_freq=int(setting["top_freq"]),
                   passage_support_credit_max_rank=int(setting["max_rank"]))


def calibration_rows() -> list[dict]:
    return (_dev5_calibration_rows() + [{**r, "set": "dev6"} for r in load_dev6()]
            + [{**r, "set": "dev7_tune"} for r in dev7_half("tune")])


def calibration_traps() -> list[dict]:
    return load_traps() + load_traps_v2() + half_v3("tune")


def n_active(setting: dict) -> int:
    return int(bool(setting["stop"])) + int(bool(setting["top_freq"])) + int(bool(setting["max_rank"]))


def selection_key(r: dict) -> tuple:
    return (-int(r["safe"]), -r["calib_correct"], -r["calib_answer_correct"], n_active(r),
            int(r["stop"]), r["top_freq"], -(r["max_rank"] or 10**9))


def is_safe_setting(r: dict) -> bool:
    return bool(
        r["clean_accuracy"] == 1.0
        and r["n_fail_open_clean"] == 0
        and r["n_spurious_write"] == 0
        and r["n_raw_pii"] == 0
        and not r["must_refuse_opened"]
        and not r["traps_opened"]
        and r["sweep_safe"]
        and r["rows_lost"] <= MAX_ROWS_LOST
        and r["answer_lost"] <= MAX_ANSWER_LOST
    )


def _public(stats: dict) -> dict:
    return {k: v for k, v in stats.items() if k not in ("ok", "decisions")}


def evaluate_setting(st: dict, rows: list[dict], traps: list[dict], base: dict, base_cfg: CopilotConfig) -> dict:
    cfg = config_for(st)
    clean = _clean_stats(cfg)
    on = score_rows(cfg, rows)
    tr = score_traps(cfg, traps)
    sw = sweep(cfg, base=base_cfg)
    errs = new_errors(base, on)
    answer_ids = {r["id"] for r in rows if r["expect_decision"] == "ANSWER"}
    r = {
        **st,
        "clean_accuracy": clean["clean_accuracy"],
        "n_fail_open_clean": clean["n_fail_open"] + clean["n_spurious_write"],
        "calib_correct": on["correct"],
        "calib_answer_correct": on["answer_correct"],
        "n_spurious_write": on["n_spurious_write"],
        "n_raw_pii": on["n_raw_pii"],
        "fixed": fixed_rows(base, on),
        "new_errors": errs,
        "rows_lost": max(0, base["correct"] - on["correct"]),
        "answer_lost": sum(e in answer_ids for e in errs),
        "must_refuse_opened": opened_must_refuse(on, rows),
        "traps_opened": tr["opened"],
        "sweep_safe": bool(sw["safe"]),
        "sweep_labelled_trap_opened": [c["query"] for c in sw["labelled_trap_opened"]],
    }
    r["safe"] = is_safe_setting(r)
    return r


def calibrate(settings: list[dict] | None = None, map_fn=map) -> dict:
    rows, traps = calibration_rows(), calibration_traps()
    base_cfg = shipped_config()
    base = score_rows(base_cfg, rows)
    base_traps = score_traps(base_cfg, traps)
    sts = settings or grid_settings()
    results = list(map_fn(lambda st: evaluate_setting(st, rows, traps, base, base_cfg), sts))
    results.sort(key=selection_key)
    chosen = results[0] if results and results[0]["safe"] else None
    return {
        "n_rows": len(rows), "n_traps": len(traps), "n_settings": len(results),
        "rows_by_set": {s: sum(r.get("set") == s for r in rows)
                        for s in ("dev", "dev2", "dev3", "dev4", "dev5_tune", "dev6", "dev7_tune")},
        "baseline_shipped": {**_public(base), "opened_must_refuse": opened_must_refuse(base, rows),
                             "traps_opened": base_traps["opened"]},
        "n_safe": sum(r["safe"] for r in results),
        "chosen": chosen, "candidate": chosen is not None,
        "results": results,
    }


def confirm_decision(on_traps: dict, base_dev7: dict, on_dev7: dict, dev7_rows: list[dict],
                     base_rob: dict, on_rob: dict, sweep_report: dict) -> dict:
    hb = base_rob["per_synonym_split"]["heldout"]
    hn = on_rob["per_synonym_split"]["heldout"]
    n_pert = max(int(base_rob.get("n_perturbed", 0) or 0), 1)
    errs = new_errors(base_dev7, on_dev7)
    opened = opened_must_refuse(on_dev7, dev7_rows)
    checks = {
        "traps_v3_confirm_none_open": on_traps["n_opened"] == 0,
        "dev7_confirm_no_new_error": not errs,
        "dev7_confirm_no_must_refuse_open": not opened,
        "clean_1": on_rob["clean_accuracy"] == 1.0,
        "robustness_no_fail_open_write_pii": on_rob["n_fail_open"] == 0
        and on_rob["n_spurious_write"] == 0 and on_rob["n_raw_pii_outputs"] == 0,
        "heldout_acc_not_down": hn["perturbed_accuracy"] >= hb["perturbed_accuracy"] - 1e-9,
        "heldout_answer_not_down": hn["by_gate"]["ANSWER"]["correct"] >= hb["by_gate"]["ANSWER"]["correct"],
        "perturbed_within_2_rows": on_rob["perturbed_accuracy"]
        >= base_rob["perturbed_accuracy"] - PERTURBED_ROWS_TOLERANCE / n_pert - 1e-9,
        "sweep_no_labelled_trap": bool(sweep_report["safe"]),
    }
    return {"checks": checks, "default_on": all(checks.values()), "dev7_new_errors": errs,
            "dev7_must_refuse_opened": opened}
