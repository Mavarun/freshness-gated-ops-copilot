"""Seed sensitivity of the shipped null-control test (pre-registered 2026-10-26, before any non-42 run).

Question (README weakness, 2026-10-25): the shipped cut q = 0.30 was chosen and
confirmed with one control sample (seed 42, 100 words) on a set where some
keep rows score 0.20 to 0.40. Does the safety result depend on which 100
controls were drawn?

Seeds (``SEEDS``): 1..20, plus 42 as the reference. Nothing else changes: the
shipped default with only ``passage_support_null_seed`` replaced. Secondary,
recorded only: the same seeds with 300 controls (``CONTROLS_SECONDARY``),
since a larger sample should make the percentile less noisy.

Rows (all already seen; no unseen set is spent): the 171 calibration rows of
``datamuse_dev5.calibration_rows`` (dev, dev2, dev3, dev4, dev5 tune), the 36
attribute traps, the 51 clean golden rows. dev5 confirm and dev6 are not used.

Per seed, ``seed_check`` records: clean accuracy; calibration correct and
ANSWER correct; must-refuse calibration rows opened; attribute traps opened.

Stability rule (``is_stable``), fixed before the run: a seed is **safe** if
clean is 1.000 and it opens no attribute trap and no must-refuse calibration
row; the shipped test is **seed-stable** if every seed is safe and every
seed's calibration correct is within ``CALIB_TOLERANCE`` (3) rows of seed 42.

Outcome is report-only. If it is not seed-stable the default stays as shipped
(changing it would need its own pre-registered test on unseen rows) and the
README records it as a weakness.
"""

from __future__ import annotations

from dataclasses import replace

from ops_copilot.attribute_traps import load_traps, score_traps
from ops_copilot.config import CopilotConfig
from ops_copilot.datamuse_dev4 import opened_must_refuse
from ops_copilot.datamuse_dev5 import calibration_rows
from ops_copilot.noun_gloss_sense_calibration import _clean_stats
from ops_copilot.wordnet_dev2 import score_rows

SEEDS = tuple(range(1, 21))
REFERENCE_SEED = 42
CONTROLS_PRIMARY = 100
CONTROLS_SECONDARY = 300
CALIB_TOLERANCE = 3


def seed_config(seed: int, controls: int = CONTROLS_PRIMARY, base: CopilotConfig | None = None) -> CopilotConfig:
    return replace(base or CopilotConfig(), passage_support_null_seed=int(seed),
                   passage_support_null_controls=int(controls))


def seed_check(cfg: CopilotConfig, rows: list[dict], traps: list[dict]) -> dict:
    clean = _clean_stats(cfg)
    s = score_rows(cfg, rows)
    t = score_traps(cfg, traps)
    return {
        "clean_accuracy": clean["clean_accuracy"],
        "calib_correct": s["correct"],
        "calib_answer_correct": s["answer_correct"],
        "must_refuse_opened": opened_must_refuse(s, rows),
        "traps_opened": t["opened"],
        "decisions": s["decisions"],
    }


def is_safe(r: dict) -> bool:
    return r["clean_accuracy"] == 1.0 and not r["traps_opened"] and not r["must_refuse_opened"]


def is_stable(results: dict[int, dict], reference: dict) -> dict:
    unsafe = sorted(s for s, r in results.items() if not is_safe(r))
    drift = sorted(s for s, r in results.items()
                   if abs(r["calib_correct"] - reference["calib_correct"]) > CALIB_TOLERANCE)
    return {"unsafe_seeds": unsafe, "drift_seeds": drift, "stable": not unsafe and not drift}


def run(controls: int = CONTROLS_PRIMARY, seeds: tuple[int, ...] = SEEDS) -> dict:
    rows, traps = calibration_rows(), load_traps()
    ref = seed_check(seed_config(REFERENCE_SEED, controls), rows, traps)
    res = {s: seed_check(seed_config(s, controls), rows, traps) for s in seeds}
    calib = [r["calib_correct"] for r in res.values()]
    flips: dict[str, int] = {}
    for r in res.values():
        for rid, dec in r["decisions"].items():
            if dec != ref["decisions"][rid]:
                flips[rid] = flips.get(rid, 0) + 1
    return {
        "controls": controls,
        "n_rows": len(rows),
        "n_traps": len(traps),
        "reference": {k: v for k, v in ref.items() if k != "decisions"},
        "seeds": {str(s): {k: v for k, v in r.items() if k != "decisions"} for s, r in res.items()},
        "calib_correct_min": min(calib),
        "calib_correct_max": max(calib),
        "n_safe_seeds": sum(is_safe(r) for r in res.values()),
        "rows_flipping_vs_42": dict(sorted(flips.items())),
        "verdict": is_stable(res, ref),
    }
