"""Pre-registered protocol for verified did-you-mean rewrites (frozen 2026-11-06).

Written before the calibration grid was run as a whole and before any confirm row
was scored. Disclosure: while building the module, arms ``context``,
``context_mc1`` and ``context_mc2`` were run once on the calibration files (dev2-dev6),
and the null control was seen there (random corpus words verify 44% of the time). No
dev7, fresh or held-out row was scored before this file.

Calibration: dev2-dev6 (spent for every older arm, fresh for this feature).
Confirm, once: dev7 + synonym_fresh (pooled) and the held-out golden synonym rows.

Selection on calibration: highest ``anchor_hit_1``, subject to
``trap_invitation <= MAX_TRAP_INVITATION`` and ``anchor_precision_1 >= MIN_PRECISION``;
ties go to the earlier arm in ``ARMS``.

Ship rule (confirm): the picked arm is turned on as an explanation field only when on the
pooled confirm rows ``anchor_precision_1 >= MIN_PRECISION`` and
``trap_invitation <= MAX_TRAP_INVITATION``, and on the held-out rows
``anchor_hit_3 >= MIN_HELDOUT_ANCHOR_3`` of 9. Otherwise it ships off. Either way the
decision on the original query never changes, so held-out ANSWER stays 0 of 9 by
construction; the protocol measures "one click away", not understanding.
"""

from __future__ import annotations

from ops_copilot.rewrite_suggest import SuggestConfig

ARMS: dict[str, SuggestConfig] = {
    "idf": SuggestConfig(rank="idf"),
    "first": SuggestConfig(rank="first"),
    "context": SuggestConfig(rank="context"),
    "context_mc1": SuggestConfig(rank="context", min_context=1),
    "context_mc2": SuggestConfig(rank="context", min_context=2),
    "context_pairs": SuggestConfig(rank="context", max_pairs=36),
    "context_mc1_pairs": SuggestConfig(rank="context", min_context=1, max_pairs=36),
}
MAX_TRAP_INVITATION = 0.40
MIN_PRECISION = 0.50
MIN_HELDOUT_ANCHOR_3 = 3
NULL_DRAWS = 6
SEED = 1106


def eligible(rates: dict) -> bool:
    return rates["trap_invitation"] <= MAX_TRAP_INVITATION and rates["anchor_precision_1"] >= MIN_PRECISION


def pick(calibration: dict[str, dict]) -> str | None:
    """Arm name picked from ``{arm: rates}``; None when no arm is eligible."""
    best, best_v = None, -1.0
    for name in ARMS:
        r = calibration.get(name)
        if r is not None and eligible(r) and r["anchor_hit_1"] > best_v:
            best, best_v = name, r["anchor_hit_1"]
    return best


def ships(confirm_rates: dict, heldout_anchor_3: int) -> bool:
    return eligible(confirm_rates) and heldout_anchor_3 >= MIN_HELDOUT_ANCHOR_3
