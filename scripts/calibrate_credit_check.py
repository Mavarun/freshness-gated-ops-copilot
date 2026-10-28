#!/usr/bin/env python3
"""Calibration grid of the credited-word check -> artifacts/credit_check_calibration.{json,md}.

Protocol: ``ops_copilot/credit_check.py`` (committed before this ran). Scores
only calibration rows: 238 rows, 51 clean, 95 traps (v1, v2, v3 tune). Settings
run in forked worker processes (``--jobs``); results do not depend on it.
"""

from __future__ import annotations

import argparse
import json
import multiprocessing as mp
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ops_copilot.credit_check import MAX_ANSWER_LOST, MAX_ROWS_LOST, calibrate  # noqa: E402

_FN = None


def _call(x):
    return _FN(x)


def pmap(jobs: int):
    def run(fn, items):
        global _FN
        _FN = fn
        if jobs <= 1:
            return [fn(x) for x in items]
        with mp.get_context("fork").Pool(jobs) as p:
            return p.map(_call, list(items), chunksize=1)
    return run


def _arm(r: dict) -> str:
    parts = (["stop"] if r["stop"] else []) + ([f"top{r['top_freq']}"] if r["top_freq"] else []) \
        + ([f"rank<={r['max_rank']}"] if r["max_rank"] else [])
    return " + ".join(parts)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--jobs", type=int, default=1)
    out = calibrate(map_fn=pmap(ap.parse_args().jobs))
    art = ROOT / "artifacts"
    (art / "credit_check_calibration.json").write_text(json.dumps(out, indent=1, sort_keys=True) + "\n")
    b = out["baseline_shipped"]
    lines = [
        "# Credited-word check: calibration grid (pre-registered, `credit_check.py`)", "",
        f"Rows: {out['n_rows']} calibration ({out['rows_by_set']}), 51 clean, {out['n_traps']} traps "
        f"(36 v1 + 40 v2 + 19 v3 tune). Baseline (shipped default): {b['correct']}/{b['n']} "
        f"(ANSWER {b['answer_correct']}/{b['n_answer']}), traps opened {', '.join(b['traps_opened']) or 'none'}, "
        f"must-refuse opened {', '.join(b['opened_must_refuse']) or 'none'}.", "",
        f"Safe = clean 1.000, no must-refuse row or calibration trap opened, sweep safe, at most "
        f"{MAX_ROWS_LOST} rows / {MAX_ANSWER_LOST} ANSWER lost. Rows sorted by the selection key.", "",
        "| arm | safe | calib correct | ANSWER | rows lost | new errors | traps opened | must-refuse opened |",
        "| :--- | :---: | ---: | ---: | ---: | :--- | :--- | :--- |",
    ]
    for r in out["results"]:
        lines.append(f"| {_arm(r)} | {'yes' if r['safe'] else 'no'} | {r['calib_correct']} | "
                     f"{r['calib_answer_correct']} | {r['rows_lost']} | {', '.join(r['new_errors']) or '-'} | "
                     f"{', '.join(r['traps_opened']) or '-'} | {', '.join(r['must_refuse_opened']) or '-'} |")
    ch = out["chosen"]
    lines += ["", f"{out['n_safe']} of {out['n_settings']} settings safe. "
              + (f"**Chosen: {_arm(ch)}** ({ch['calib_correct']}/{out['n_rows']}, {ch['rows_lost']} rows lost)."
                 if ch else "**No candidate: the check ships off and no confirm row is scored.**"), ""]
    (art / "credit_check_calibration.md").write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
