"""Seed-free null test: protocol (pre-registered 2026-10-27, before any run on traps v2).

Question (README weakness, 2026-10-26): the shipped null test (100 seeded
controls, q = 0.30, sticky) refuses the 36 attribute traps for seed 42 only.
``passage_null_exact`` puts a number on it: over 10,000 control samples it
opens no trap with probability 0.047. Can a test that has no sample at all
(``passage_support_null_pool``: the percentile over the whole 5,067-word pool)
refuse the traps at an acceptable cost?

Disclosed before this file: the pool grid q = 0.20 .. 0.50 was evaluated on the
171 calibration rows and the 36 first-set traps (``artifacts/passage_null_exact.md``):
q <= 0.36 opens at-22 (pool percentile 0.363), q = 0.38 is the first setting that
opens none (85 vs 88 of 171), q = 0.40 costs 5 rows. No row of
``attribute_traps_v2.jsonl`` has been scored by any config.

Arms (``grid_settings``): pool mode, sticky veto, q in ``GRID_Q`` (0.30 .. 0.50
step 0.02). Baseline: the shipped default (seed 42).

Calibration rows: the 171 rows of ``datamuse_dev5.calibration_rows``, the 51
clean golden rows, **all 36** first-set traps (spent) and the 20 **tune** traps of
the second set.

Safe (``is_safe_setting``): clean 1.000 with no fail-open or spurious write; no
spurious write or raw PII on calibration rows; no must-refuse calibration row
opens; no calibration trap opens; the tests/ literal sweep opens no labelled trap;
cost vs the shipped default at most ``MAX_ROWS_LOST`` (6) calibration rows and
``MAX_ANSWER_LOST`` (3) ANSWER rows.

Selection (``select``): a trap just below the cut flips with any small shift in
scores, so the chosen q must keep a margin: the **smallest q that is safe and
whose next-lower grid point is also safe** (so every calibration trap sits at
least one grid step, 0.02, below the cut). No such q: the knob ships off and no
confirm row is scored.

One-shot confirm (``confirm_decision``), on rows never seen while designing:

- the 20 confirm traps of the second set: the chosen arm opens none;
- 203-row robustness run: clean 1.000; no fail-open, spurious write or raw PII;
  held-out accuracy and held-out ANSWER not below the shipped default; overall
  perturbed accuracy within 2 rows of it;
- the sweep opens no labelled trap.

Recorded only, never used to decide: the shipped default on the 20 confirm
traps, its probability over 10,000 control samples of opening at least one of
them (``passage_null_exact`` trees), and the arm's cost on the spent dev6 set.

If every check passes, the default becomes pool mode at the chosen q and every
report-only artifact is re-pinned with its cost; otherwise the knob stays off.
"""

from __future__ import annotations

from dataclasses import replace

from ops_copilot.attribute_traps import load_traps, score_traps
from ops_copilot.attribute_traps_v2 import half_v2
from ops_copilot.config import CopilotConfig
from ops_copilot.datamuse_dev4 import opened_must_refuse
from ops_copilot.datamuse_dev5 import calibration_rows
from ops_copilot.noun_gloss_sense_calibration import _clean_stats
from ops_copilot.safety_sweep import sweep
from ops_copilot.wordnet_dev2 import fixed_rows, new_errors, score_rows

GRID_Q = tuple(round(0.30 + 0.02 * i, 2) for i in range(11))
MAX_ROWS_LOST = 6
MAX_ANSWER_LOST = 3
PERTURBED_ROWS_TOLERANCE = 2


def shipped_config() -> CopilotConfig:
    """The shipped default before this slice (seed-42 sample): every baseline here."""
    return replace(CopilotConfig(), passage_support_null_pool=False, passage_support_null_min=0.30,
                   passage_support_null_controls=100, passage_support_null_seed=42,
                   passage_support_null_sticky=True, passage_support_credit_stop=False)


def grid_settings() -> list[dict]:
    return [{"null_min": q, "pool": True, "sticky": True} for q in GRID_Q]


def config_for(setting: dict, base: CopilotConfig | None = None) -> CopilotConfig:
    return replace(base or shipped_config(), passage_support_null_pool=bool(setting["pool"]),
                   passage_support_null_min=float(setting["null_min"]),
                   passage_support_null_sticky=bool(setting["sticky"]))


def calibration_traps() -> list[dict]:
    return load_traps() + half_v2("tune")


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


def select(results: list[dict]) -> dict | None:
    """Smallest safe q whose next-lower grid point is also safe (one-step margin)."""
    by_q = {round(r["null_min"], 2): r for r in results}
    qs = sorted(by_q)
    for lo, q in zip(qs, qs[1:]):
        if by_q[q]["safe"] and by_q[lo]["safe"]:
            return by_q[q]
    return None


def _public(stats: dict) -> dict:
    return {k: v for k, v in stats.items() if k not in ("ok", "decisions")}


def calibrate(settings: list[dict] | None = None) -> dict:
    rows, traps = calibration_rows(), calibration_traps()
    base_cfg = shipped_config()
    base = score_rows(base_cfg, rows)
    base_traps = score_traps(base_cfg, traps)
    answer_ids = {r["id"] for r in rows if r["expect_decision"] == "ANSWER"}
    results = []
    for st in settings or grid_settings():
        cfg = config_for(st)
        clean = _clean_stats(cfg)
        on = score_rows(cfg, rows)
        tr = score_traps(cfg, traps)
        sw = sweep(cfg, base=base_cfg)
        errs = new_errors(base, on)
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
        results.append(r)
    chosen = select(results)
    return {
        "n_rows": len(rows), "n_traps": len(traps), "n_settings": len(results),
        "baseline_shipped": {**_public(base), "opened_must_refuse": opened_must_refuse(base, rows),
                             "traps_opened": base_traps["opened"]},
        "n_safe": sum(r["safe"] for r in results),
        "chosen": chosen, "candidate": chosen is not None,
        "results": results,
    }


def confirm_decision(on_traps: dict, base_rob: dict, on_rob: dict, sweep_report: dict) -> dict:
    hb = base_rob["per_synonym_split"]["heldout"]
    hn = on_rob["per_synonym_split"]["heldout"]
    n_pert = max(int(base_rob.get("n_perturbed", 0) or 0), 1)
    checks = {
        "traps_v2_confirm_none_open": on_traps["n_opened"] == 0,
        "clean_1": on_rob["clean_accuracy"] == 1.0,
        "robustness_no_fail_open_write_pii": on_rob["n_fail_open"] == 0
        and on_rob["n_spurious_write"] == 0 and on_rob["n_raw_pii_outputs"] == 0,
        "heldout_acc_not_down": hn["perturbed_accuracy"] >= hb["perturbed_accuracy"] - 1e-9,
        "heldout_answer_not_down": hn["by_gate"]["ANSWER"]["correct"] >= hb["by_gate"]["ANSWER"]["correct"],
        "perturbed_within_2_rows": on_rob["perturbed_accuracy"]
        >= base_rob["perturbed_accuracy"] - PERTURBED_ROWS_TOLERANCE / n_pert - 1e-9,
        "sweep_no_labelled_trap": bool(sweep_report["safe"]),
    }
    return {"checks": checks, "default_on": all(checks.values())}
