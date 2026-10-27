#!/usr/bin/env python3
"""Seed-free view of the shipped null test -> artifacts/passage_null_exact.{json,md}.

Report-only (``ops_copilot/passage_null_exact.py``): rows already used by the
2026-10-26 seed sweep (171 calibration rows, 36 spent attribute traps); no
unseen row is scored and no config changes.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ops_copilot.attribute_traps import load_traps  # noqa: E402
from ops_copilot.datamuse_dev5 import calibration_rows  # noqa: E402
from ops_copilot.passage_null_exact import (  # noqa: E402
    build_trees,
    depth,
    evaluate_sample,
    pool_decision,
    sample_distribution,
    seed_indices,
)
from ops_copilot.synonym_dev4 import OPENING  # noqa: E402

POOL_GRID = tuple(round(0.20 + 0.02 * i, 2) for i in range(16))  # 0.20 .. 0.50


def _score(d, rows, traps):
    ans = [r for r in rows if r["expect_decision"] == "ANSWER"]
    return {
        "calib_correct": sum(d[r["id"]] == r["expect_decision"] for r in rows),
        "calib_answer_correct": sum(d[r["id"]] == "ANSWER" for r in ans),
        "traps_opened": sorted(t["id"] for t in traps if d[t["id"]] in OPENING),
        "must_refuse_opened": sorted(r["id"] for r in rows
                                     if r["expect_decision"] not in OPENING and d[r["id"]] in OPENING),
    }


def main() -> int:
    rows, traps = calibration_rows(), load_traps()
    trees, pool = build_trees(rows + traps)
    seed42 = _score(evaluate_sample(trees, seed_indices(pool, 42)), rows, traps)
    dist = {k: sample_distribution(trees, rows, traps, len(pool), k=k) for k in (100, 300)}
    grid = [{"q": q, **_score(pool_decision(trees, q), rows, traps)} for q in POOL_GRID]
    live = {rid: t for rid, t in trees.items() if t.decision is None}
    trap_calls = {}
    for t in traps:
        node, out = live.get(t["id"]), []
        stack = [node] if node else []
        while stack:
            n = stack.pop()
            if n.decision is None:
                out.append(round(float(np.mean(n.below)), 4))
                stack += [n.vetoed, n.passed]
        if out:
            trap_calls[t["id"]] = out
    out = {"n_pool": len(pool), "n_rows": len(rows), "n_traps": len(traps), "n_live_rows": len(live),
           "max_depth": max(depth(t) for t in trees.values()), "seed_42": seed42,
           "sample_distribution": dist, "pool_grid": grid, "trap_call_pool_percentiles": trap_calls}
    art = ROOT / "artifacts"
    (art / "passage_null_exact.json").write_text(json.dumps(out, indent=1, sort_keys=True) + "\n")

    d1, d3 = dist[100], dist[300]
    lines = [
        "# The shipped null test without a seed (report-only, `passage_null_exact.py`)", "",
        f"Pool: {len(pool)} control words. {len(live)} of {len(trees)} rows reach the null test "
        f"(at most {out['max_depth']} calls per row). Trees reproduce all 21 seeds of the 2026-10-26 sweep "
        "exactly (tested).", "",
        f"Seed 42 (shipped): calibration {seed42['calib_correct']}/{len(rows)}, traps opened "
        f"{len(seed42['traps_opened'])}/{len(traps)}.", "",
        f"## Over {d1['n_samples']:,} uniform control samples (shared by every row, as one seed is)", "",
        "| controls | P(no trap opens) | P(safe) | mean traps opened | calibration correct, mean [5%, 95%] |",
        "| ---: | ---: | ---: | ---: | :--- |",
    ]
    for d in (d1, d3):
        lines.append(f"| {d['k']} | {d['p_no_trap_open']:.3f} | {d['p_safe']:.3f} | {d['mean_traps_opened']:.2f} | "
                     f"{d['correct_mean']:.1f} [{d['correct_p05_p95'][0]}, {d['correct_p05_p95'][1]}] |")
    lines += ["", "Traps opened per sample (100 controls): "
              + ", ".join(f"{k}: {v}" for k, v in d1["traps_opened_hist"].items()) + ".", "",
              "| trap | P(open), 100 controls | P(open), 300 controls | pool percentile of each call |",
              "| :--- | ---: | ---: | :--- |"]
    for rid in sorted(set(d1["p_open"]) | set(d3["p_open"])):
        if rid in trap_calls:
            lines.append(f"| {rid} | {d1['p_open'].get(rid, 0):.3f} | {d3['p_open'].get(rid, 0):.3f} | "
                         f"{', '.join(f'{x:.3f}' for x in trap_calls[rid])} |")
    lines += ["", "## Whole-pool percentile (seed-free mode) on the same seen rows", "",
              "| q | calibration correct | ANSWER correct | traps opened | must-refuse opened |",
              "| ---: | ---: | ---: | :--- | :--- |"]
    for g in grid:
        lines.append(f"| {g['q']:.2f} | {g['calib_correct']} | {g['calib_answer_correct']} | "
                     f"{', '.join(g['traps_opened']) or '-'} | {', '.join(g['must_refuse_opened']) or '-'} |")
    lines.append("")
    (art / "passage_null_exact.md").write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
