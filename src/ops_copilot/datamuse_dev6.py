"""One-shot confirm of the word-meaning Datamuse arm on dev6 (pre-registered 2026-10-26, before any run on dev6).

Hypothesis (``artifacts/datamuse_dev5_recalibration.md``, 2026-10-25): on top of
the null-test default, the word-meaning-gated, unknown-words-only Datamuse arm
**rank <= 100, one neighbour, context >= 2, sense >= 0.30** (``ARM``) answers
more ops / everyday paraphrases without opening a must-refuse row: 98 vs 88 of
171 calibration rows (ANSWER 33 vs 24), no new error, no attribute trap
opened. Those 171 rows include four burned sets, so the +10 is a selection
estimate, not evidence.

The arm is **frozen** as a literal, and a test pins it to the
recalibration artifact's ``chosen``. There is no grid and no tuning on dev6.

Rows: all 45 dev6 rows (``synonym_dev6.py``; no tune half). Before this file was
committed no config had been scored on any dev6 row.

Decision (``confirm_decision``), every check must pass for ``default_on``:

1. dev4's confirm rule unchanged (``datamuse_dev4.confirm_decision``) on the 45
   dev6 rows, the 203-row robustness run and the tests/ literal sweep:
   strictly more correct dev6 rows; dev6 ANSWER not down; **no new error** on
   any dev6 row; no fail-open, spurious write or raw PII; clean 1.000;
   held-out accuracy and ANSWER not down; no dev6 must-refuse row opens; the
   sweep opens no labelled trap;
2. **attribute traps**: all 36 stay refused (``attribute_traps.score_traps``;
   both halves were spent on 2026-10-25, so this is a no-harm check only).

Recorded, never used to decide: an exact two-sided sign test on the dev6
rows that change (``sign_test_p``), so a +1 gain is not read as evidence; the
fresh general-English set; per-row decisions.

If any check fails the flag ships off, dev6 is spent, and the next attempt
needs a dev7 set.
"""

from __future__ import annotations

from math import comb

from ops_copilot.attribute_traps import load_traps, score_traps
from ops_copilot.config import CopilotConfig
from ops_copilot.datamuse_dev4 import confirm_decision as _dev4_confirm
from ops_copilot.datamuse_dev4 import off_config, opened_must_refuse
from ops_copilot.datamuse_dev5 import config_for as _dev5_config

# Frozen 2026-10-26 from artifacts/datamuse_dev5_recalibration.json["chosen"].
ARM = {"max_rank": 100, "max_neighbours": 1, "context_min": 2, "sense_min": 0.30}
N_ATTRIBUTE_TRAPS = 36

__all__ = ["ARM", "arm_config", "off_config", "opened_must_refuse", "confirm_decision", "sign_test_p"]


def arm_config(base: CopilotConfig | None = None) -> CopilotConfig:
    """The frozen arm on top of the shipped default (or ``base``)."""
    return _dev5_config(ARM, base)


def sign_test_p(n_fixed: int, n_broken: int) -> float:
    """Exact two-sided sign test on discordant rows (McNemar exact); 1.0 if none."""
    n = n_fixed + n_broken
    if n == 0:
        return 1.0
    k = min(n_fixed, n_broken)
    tail = sum(comb(n, i) for i in range(k + 1)) / 2**n
    return min(1.0, 2 * tail)


def confirm_decision(off_confirm: dict, on_confirm: dict, off_rob: dict, on_rob: dict,
                     confirm_rows: list[dict], sweep_report: dict, traps_on: dict) -> dict:
    base = _dev4_confirm(off_confirm, on_confirm, off_rob, on_rob, confirm_rows, sweep_report)
    checks = {**base["checks"], "attribute_traps_all_refused": traps_on["n_opened"] == 0}
    return {"checks": checks, "default_on": all(checks.values()),
            "must_refuse_opened": base["must_refuse_opened"], "traps_opened": traps_on["opened"]}


def score_attribute_traps(cfg: CopilotConfig) -> dict:
    rows = load_traps()
    if len(rows) != N_ATTRIBUTE_TRAPS:
        raise ValueError(f"expected {N_ATTRIBUTE_TRAPS} attribute traps, got {len(rows)}")
    return score_traps(cfg, rows)
