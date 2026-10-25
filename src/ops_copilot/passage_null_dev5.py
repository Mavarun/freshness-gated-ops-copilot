"""Null-control test on passage rescues (pre-registered 2026-10-25, before any grid run).

Problem (PR #28, ``artifacts/passage_sense_probe.md``): the shipped default
answers the must-refuse dev5 trap d5-38 (``What colour is the checkout_retry
feature flag?``) through the passage rescue ``colour <- default``. The only
fix tried (the credited word must be a counter-fitted substitute) costs 36
correct calibration rows (92 -> 57 of 171).

Size of the hole (``attribute_traps.py``, tune half only, shipped default):
5 of 18 attribute traps open (``price``, ``flavour`` x2, ``weight``,
``expensive``), in all four question forms, with credits such as
``flavour <- other`` and ``weight <- utc``.

Hypothesis: when a passage answers the question *because of* the missing
word, swapping that word for an unrelated one should lower the classifier's
probability. When the probability comes from the topic alone, most unrelated
words score as high. ``passage_support_null_min`` = *q* rescues a word only
if at least a fraction *q* of 100 seeded control words (domain-vector words
outside the corpus) score strictly below it on the same passage.

Disclosed before this file was written (exploration, not committed): on the
171 calibration rows plus the 18 trap ``tune`` rows, a draft of the same test
(another control sample) was printed for every row whose decision depends on
the rescue. It suggested that no *q* both closes every trap and keeps every
correct row: closing all traps needed *q* around 0.40 and cost about four
correct rows (``plan``, ``execute``, ``lifespan``, ``diagnostics``), three
of which are refusals that would only change refusal type. So the rule below
allows a bounded cost; the strict no-new-error rule used for synonym arms
would reject every setting by construction.

Grid (``GRID_Q``): q in {0.10, 0.20, 0.30, 0.40, 0.50}; 100 controls, seed 42.

Calibration rows: dev5 calibration (15 dev + 43 dev2 + 45 dev3 + 44 dev4 +
24 dev5 tune = 171), the 18 attribute-trap ``tune`` rows, the 51 clean golden
rows and the tests/ literal sweep. dev5 ``confirm``, the trap ``confirm`` half
and held-out rows are never scored here.

Safe (``is_safe_setting``):

1. clean golden 1.000, no fail-open or spurious write there;
2. calibration: no spurious write, no raw PII;
3. **no must-refuse calibration row opens** (this includes d5-38) and **no
   attribute-trap tune row opens**;
4. the sweep opens no labelled trap;
5. cost: at most ``MAX_NEW_ERRORS`` = 9 calibration rows that the shipped
   default gets right become wrong (10% of its 92), and at most
   ``MAX_ANSWER_LOSS`` = 3 of them are ANSWER rows (a refusal that changes
   type, e.g. REFUSE_STALE -> REFUSE_UNGROUNDED, is wrong but not unsafe).

Selection (``selection_key``): safe; most calibration correct; most
calibration ANSWER correct; **higher q** on ties (the stricter test wins).

Candidate: any safe setting. If none is safe, the test ships off and no
confirm row is scored.

Confirm (one shot, ``confirm_decision``) on dev5 confirm (20 rows), the trap
confirm half (18 rows, unseen attributes), the 203-row robustness run and the
sweep. Default on only if all hold:

- dev5 confirm opens no must-refuse row, and correct >= shipped default - 1;
- trap confirm opens no row (shipped default's opens are reported);
- robustness: clean 1.000; no fail-open, spurious write or raw PII; held-out
  accuracy >= shipped default - 1 row's worth, held-out ANSWER not down;
- the sweep opens no labelled trap.

Amendment v2 (pre-registered 2026-10-25 after the v1 calibration and the
post-hoc diagnosis, before any v2 grid run; both confirm halves still unseen):

v1 found no safe setting (``artifacts/passage_null_calibration.md``) and the
diagnosis (``artifacts/passage_null_diagnosis.md``) found why: the rescue is
retried per supporting chunk, so a trap vetoed on one chunk passes on another
(at-25: 0.12 then 0.61). v2 adds ``passage_support_null_sticky``: a word the
test vetoes for a query on any part stays vetoed for that query. Disclosed:
before this amendment was written, q = 0.50 with the sticky veto was run on
at-22 and at-25 only (both refused). Grid, safe rule, cost caps, selection
key and confirm rule are v1's unchanged; the v1 grid is not re-selected.
"""

from __future__ import annotations

from dataclasses import replace

from ops_copilot.attribute_traps import half as trap_half
from ops_copilot.attribute_traps import score_traps
from ops_copilot.config import CopilotConfig
from ops_copilot.datamuse_dev4 import opened_must_refuse
from ops_copilot.datamuse_dev5 import calibration_rows
from ops_copilot.noun_gloss_sense_calibration import _clean_stats
from ops_copilot.safety_sweep import sweep
from ops_copilot.wordnet_dev2 import fixed_rows, new_errors, score_rows

GRID_Q = (0.10, 0.20, 0.30, 0.40, 0.50)
N_CONTROLS = 100
MAX_NEW_ERRORS = 9
MAX_ANSWER_LOSS = 3

__all__ = ["calibration_rows", "opened_must_refuse"]


def pre_change_config() -> CopilotConfig:
    """The shipped default before this slice (null test off): every baseline here."""
    return replace(CopilotConfig(), passage_support_null_min=0.0, passage_support_null_sticky=False)


def grid_settings() -> list[dict]:
    return [{"null_min": q} for q in GRID_Q]


def grid_settings_v2() -> list[dict]:
    return [{"null_min": q, "sticky": True} for q in GRID_Q]


def config_for(setting: dict, base: CopilotConfig | None = None) -> CopilotConfig:
    return replace(
        base or CopilotConfig(),
        passage_support_null_min=float(setting["null_min"]),
        passage_support_null_controls=N_CONTROLS,
        passage_support_null_sticky=bool(setting.get("sticky", False)),
    )


def is_safe_setting(clean: dict, on: dict, must_refuse_opened: list[str], traps_opened: list[str],
                    sweep_report: dict, n_new_errors: int, n_answer_lost: int) -> bool:
    return bool(
        clean["clean_accuracy"] == 1.0
        and clean["n_fail_open"] == 0
        and clean["n_spurious_write"] == 0
        and on["n_spurious_write"] == 0
        and on["n_raw_pii"] == 0
        and not must_refuse_opened
        and not traps_opened
        and sweep_report["safe"]
        and n_new_errors <= MAX_NEW_ERRORS
        and n_answer_lost <= MAX_ANSWER_LOSS
    )


def selection_key(r: dict) -> tuple:
    return (-int(r["safe"]), -r["calib_correct"], -r["calib_answer_correct"], -r["null_min"])


def _public(stats: dict) -> dict:
    return {k: v for k, v in stats.items() if k not in ("ok", "decisions")}


def calibrate(settings: list[dict] | None = None, rows: list[dict] | None = None,
              traps: list[dict] | None = None) -> dict:
    rows = calibration_rows() if rows is None else rows
    traps = trap_half("tune") if traps is None else traps
    answer_ids = {r["id"] for r in rows if r["expect_decision"] == "ANSWER"}
    off_cfg = pre_change_config()
    off = score_rows(off_cfg, rows)
    off_traps = score_traps(off_cfg, traps)
    results = []
    for st in settings or grid_settings():
        cfg = config_for(st)
        clean = _clean_stats(cfg)
        on = score_rows(cfg, rows)
        errs = new_errors(off, on)
        opened = opened_must_refuse(on, rows)
        tr = score_traps(cfg, traps)
        sw = sweep(cfg, base=off_cfg)
        n_ans_lost = sum(e in answer_ids for e in errs)
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
                "new_errors": errs,
                "n_answer_lost": n_ans_lost,
                "must_refuse_opened": opened,
                "traps_opened": tr["opened"],
                "traps_opened_by_form": tr["opened_by_form"],
                "sweep_n_opened": sw["n_opened"],
                "sweep_labelled_trap_opened": [c["query"] for c in sw["labelled_trap_opened"]],
                "safe": is_safe_setting(clean, on, opened, tr["opened"], sw, len(errs), n_ans_lost),
            }
        )
    results.sort(key=selection_key)
    chosen = results[0]
    return {
        "n_rows": len(rows),
        "n_trap_rows": len(traps),
        "n_settings": len(results),
        "baseline_off": {**_public(off), "clean": _clean_stats(off_cfg),
                         "opened_must_refuse": opened_must_refuse(off, rows),
                         "traps_opened": off_traps["opened"], "traps_opened_by_form": off_traps["opened_by_form"]},
        "chosen": chosen,
        "n_safe": sum(r["safe"] for r in results),
        "candidate": bool(chosen["safe"]),
        "results": results,
    }


def confirm_decision(off_confirm: dict, on_confirm: dict, confirm_rows: list[dict], on_traps: dict,
                     off_rob: dict, on_rob: dict, sweep_report: dict) -> dict:
    ho = off_rob["per_synonym_split"]["heldout"]
    hn = on_rob["per_synonym_split"]["heldout"]
    n_held = max(int(ho.get("n", 0) or 0), 1)
    checks = {
        "dev5_confirm_must_refuse_held": not opened_must_refuse(on_confirm, confirm_rows),
        "dev5_confirm_correct_within_1": on_confirm["correct"] >= off_confirm["correct"] - 1,
        "traps_confirm_none_open": on_traps["n_opened"] == 0,
        "clean_1": on_rob["clean_accuracy"] == 1.0,
        "robustness_no_fail_open_write_pii": on_rob["n_fail_open"] == 0
        and on_rob["n_spurious_write"] == 0
        and on_rob["n_raw_pii_outputs"] == 0,
        "heldout_acc_within_1_row": hn["perturbed_accuracy"] >= ho["perturbed_accuracy"] - 1.0 / n_held - 1e-9,
        "heldout_answer_not_down": hn["by_gate"]["ANSWER"]["correct"] >= ho["by_gate"]["ANSWER"]["correct"],
        "sweep_no_labelled_trap": bool(sweep_report["safe"]),
    }
    return {"checks": checks, "default_on": all(checks.values())}
