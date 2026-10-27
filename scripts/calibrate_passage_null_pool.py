#!/usr/bin/env python3
"""Calibration grid of the seed-free null test -> artifacts/passage_null_pool_calibration.{json,md}.

Protocol: ``ops_copilot/passage_null_pool.py`` (committed before this ran).
Scores only calibration rows: 171 rows, 51 clean, 36 first-set traps, 20 v2 tune traps.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ops_copilot.passage_null_pool import MAX_ANSWER_LOST, MAX_ROWS_LOST, calibrate  # noqa: E402


def main() -> int:
    out = calibrate()
    art = ROOT / "artifacts"
    (art / "passage_null_pool_calibration.json").write_text(json.dumps(out, indent=1, sort_keys=True) + "\n")
    b = out["baseline_shipped"]
    lines = [
        "# Seed-free null test: calibration grid (pre-registered, `passage_null_pool.py`)", "",
        f"Rows: {out['n_rows']} calibration, 51 clean, {out['n_traps']} traps (36 first set + 20 v2 tune). "
        f"Baseline (shipped, seed 42): {b['correct']}/{b['n']} (ANSWER {b['answer_correct']}/{b['n_answer']}), "
        f"traps opened {', '.join(b['traps_opened']) or 'none'}.", "",
        f"Safe = clean 1.000, no must-refuse or trap opened, sweep safe, at most {MAX_ROWS_LOST} rows / "
        f"{MAX_ANSWER_LOST} ANSWER lost. Selection: smallest safe q whose lower grid neighbour is also safe.", "",
        "| q | safe | calib correct | ANSWER | rows lost | new errors | traps opened | must-refuse opened |",
        "| ---: | :---: | ---: | ---: | ---: | :--- | :--- | :--- |",
    ]
    for r in out["results"]:
        lines.append(f"| {r['null_min']:.2f} | {'yes' if r['safe'] else 'no'} | {r['calib_correct']} | "
                     f"{r['calib_answer_correct']} | {r['rows_lost']} | {', '.join(r['new_errors']) or '-'} | "
                     f"{', '.join(r['traps_opened']) or '-'} | {', '.join(r['must_refuse_opened']) or '-'} |")
    ch = out["chosen"]
    lines += ["", f"{out['n_safe']} of {out['n_settings']} settings safe. "
              + (f"**Chosen: q = {ch['null_min']:.2f}** ({ch['calib_correct']}/{out['n_rows']}, "
                 f"{ch['rows_lost']} rows lost)." if ch else "**No candidate: the knob ships off.**"), ""]
    (art / "passage_null_pool_calibration.md").write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
