#!/usr/bin/env python3
"""Calibrate the null-control test on passage rescues -> artifacts/passage_null_calibration.{json,md}
(``--v2``: the sticky-veto amendment -> artifacts/passage_null_v2_calibration.{json,md}).

Protocol: ``ops_copilot.passage_null_dev5`` (pre-registered). Scores the
shipped default and each q on the 171 dev5 calibration rows, the 18
attribute-trap tune rows, clean golden and the tests/ sweep. Never touches
dev5 confirm, the trap confirm half or held-out rows.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ops_copilot.passage_null_dev5 import calibrate, grid_settings, grid_settings_v2  # noqa: E402


def main() -> int:
    v2 = "--v2" in sys.argv[1:]
    rep = calibrate(grid_settings_v2() if v2 else grid_settings())
    name = "passage_null_v2_calibration" if v2 else "passage_null_calibration"
    art = ROOT / "artifacts"
    (art / f"{name}.json").write_text(json.dumps(rep, indent=2, sort_keys=True) + "\n")
    b = rep["baseline_off"]
    lines = [
        "# Null-control test on passage rescues: calibration" + (" (v2, sticky veto)" if v2 else " (v1)"),
        "",
        f"Rows: {rep['n_rows']} dev5 calibration rows + {rep['n_trap_rows']} attribute-trap tune rows "
        "(no dev5 confirm, no trap confirm, no held-out), 51 clean golden, tests/ sweep. 100 controls, seed 42.",
        "",
        "| q | safe | calib correct | calib ANSWER | new errors (ANSWER) | must-refuse opened | traps opened | clean |",
        "| ---: | :---: | ---: | ---: | ---: | :--- | ---: | ---: |",
        f"| off (shipped) | - | {b['correct']}/{b['n']} | {b['answer_correct']}/{b['n_answer']} | - | "
        f"{', '.join(b['opened_must_refuse']) or '-'} | {len(b['traps_opened'])}/{rep['n_trap_rows']} | "
        f"{b['clean']['clean_accuracy']:.3f} |",
    ]
    for r in sorted(rep["results"], key=lambda r: r["null_min"]):
        lines.append(
            f"| {r['null_min']:.2f} | {'yes' if r['safe'] else 'no'} | {r['calib_correct']}/{rep['n_rows']} | "
            f"{r['calib_answer_correct']}/{b['n_answer']} | {len(r['new_errors'])} ({r['n_answer_lost']}) | "
            f"{', '.join(r['must_refuse_opened']) or '-'} | {len(r['traps_opened'])}/{rep['n_trap_rows']} | "
            f"{r['clean_accuracy']:.3f} |"
        )
    c = rep["chosen"]
    lines += [
        "",
        f"Safe settings: {rep['n_safe']} of {rep['n_settings']}. Chosen: q = {c['null_min']:.2f} "
        f"({'candidate' if rep['candidate'] else 'no candidate: ships off'}).",
        f"Chosen new errors: {', '.join(c['new_errors']) or '-'}; fixed: {', '.join(c['fixed']) or '-'}.",
        "",
    ]
    (art / f"{name}.md").write_text("\n".join(lines))
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
