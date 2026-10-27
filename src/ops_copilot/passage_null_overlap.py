"""Post-hoc (2026-10-27, after the spent v2 confirm): can any percentile cut separate traps from keep rows?

The one-shot confirm failed on at2-01 (``What taste is the LaunchDarkly
checkout_retry flag?``), answered at a pool percentile of 0.408 against the
chosen cut 0.40. This module asks whether *any* cut could have worked, using
the decision trees of ``passage_null_exact`` walked with the whole-pool
percentile (pool mode) at every cut on a fine grid:

- for each must-refuse row (both trap sets, must-refuse calibration rows) the
  **open-up-to cut**: the largest grid q at which pool mode still opens it;
- for each ANSWER calibration row that pool mode answers correctly at some q,
  the **kept-up-to cut**: the largest q at which it is still answered.

A cut q is free and safe only if every trap's open-up-to cut is below q and
every keep row's kept-up-to cut is at or above q. Selects nothing and changes
no config; every trap set involved is spent.
"""

from __future__ import annotations

import numpy as np

from ops_copilot.passage_null_exact import Node, build_trees, pool_decision
from ops_copilot.synonym_dev4 import OPENING

FINE_Q = tuple(round(x, 3) for x in np.arange(0.0, 1.0005, 0.002))


def credited_words(trees: dict[str, Node]) -> dict[str, list[tuple[str, str, float]]]:
    """Row id -> (query word, credited passage word, pool percentile) of every call in its tree."""
    out = {}
    for rid, t in trees.items():
        calls, stack = [], [t]
        while stack:
            n = stack.pop()
            if n.decision is None:
                calls.append((n.word, n.credited, round(float(np.mean(n.below)), 4)))
                stack += [n.vetoed, n.passed]
        if calls:
            out[rid] = calls
    return out


def cut_profile(trees: dict[str, Node], rows: list[dict], grid: tuple[float, ...] = FINE_Q) -> dict:
    want = {r["id"]: r["expect_decision"] for r in rows}
    live = {rid: t for rid, t in trees.items() if t.decision is None}
    by_q = {q: pool_decision(live, q) for q in grid}
    open_up_to, kept_up_to = {}, {}
    for rid in live:
        if want[rid] not in OPENING:
            qs = [q for q in grid if by_q[q][rid] in OPENING]
            if qs:
                open_up_to[rid] = max(qs)
        elif want[rid] == "ANSWER":
            qs = [q for q in grid if by_q[q][rid] == "ANSWER"]
            if qs and min(qs) == grid[0]:  # answered once the null test is weak enough
                kept_up_to[rid] = max(qs)
    worst_trap = max(open_up_to.values(), default=-1.0)
    free_safe = [q for q in grid if q > worst_trap and all(k >= q for k in kept_up_to.values())]
    return {
        "open_up_to": dict(sorted(open_up_to.items(), key=lambda kv: -kv[1])),
        "kept_up_to": dict(sorted(kept_up_to.items(), key=lambda kv: kv[1])),
        "worst_trap_cut": worst_trap,
        "keep_rows_below_worst_trap": sorted(r for r, k in kept_up_to.items() if k <= worst_trap),
        "free_and_safe_cuts": free_safe,
    }


def run(rows: list[dict]) -> dict:
    trees, pool = build_trees(rows)
    return {"n_pool": len(pool), "n_rows": len(rows), "profile": cut_profile(trees, rows),
            "calls": credited_words(trees)}
