#!/usr/bin/env python3
"""Seed sensitivity of the shipped null-control test -> artifacts/passage_null_seeds.{json,md}.

Protocol: ``ops_copilot/passage_null_seeds.py`` (committed before this ran).
Report-only: never changes a config and exits 0 whatever the verdict.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ops_copilot.passage_null_seeds import CONTROLS_PRIMARY, CONTROLS_SECONDARY, run  # noqa: E402


def _block(r: dict, title: str) -> list[str]:
    ref, v = r["reference"], r["verdict"]
    out = [
        f"## {title}", "",
        f"Seed 42: calibration {ref['calib_correct']}/{r['n_rows']} (ANSWER {ref['calib_answer_correct']}), "
        f"traps opened {len(ref['traps_opened'])}/{r['n_traps']}, must-refuse opened "
        f"{', '.join(ref['must_refuse_opened']) or 'none'}, clean {ref['clean_accuracy']:.3f}.",
        f"Seeds 1-20: calibration {r['calib_correct_min']}-{r['calib_correct_max']}; "
        f"{r['n_safe_seeds']} of {len(r['seeds'])} seeds safe; unsafe seeds: {v['unsafe_seeds'] or 'none'}; "
        f"seeds drifting > 3 rows: {v['drift_seeds'] or 'none'}. **Seed-stable: {'yes' if v['stable'] else 'no'}.**",
        "",
        "| seed | clean | calib correct | calib ANSWER | traps opened | must-refuse opened |",
        "| ---: | ---: | ---: | ---: | :--- | :--- |",
    ]
    for s, x in r["seeds"].items():
        out.append(f"| {s} | {x['clean_accuracy']:.3f} | {x['calib_correct']} | {x['calib_answer_correct']} | "
                   f"{', '.join(x['traps_opened']) or '-'} | {', '.join(x['must_refuse_opened']) or '-'} |")
    flips = ", ".join(f"{k} ({n})" for k, n in r["rows_flipping_vs_42"].items())
    out += ["", f"Calibration rows whose decision differs from seed 42 (number of seeds): {flips or 'none'}.", ""]
    return out


def main() -> int:
    prim, sec = run(CONTROLS_PRIMARY), run(CONTROLS_SECONDARY)
    out = {"primary": prim, "secondary_300_controls": sec}
    lines = ["# Seed sensitivity of the shipped null-control test (pre-registered, `passage_null_seeds.py`)", "",
             "Shipped default with only the control-word seed (and, secondary, the control count) changed. "
             "Rows: 171 calibration rows, 36 attribute traps, 51 clean golden; no unseen set is used.", ""]
    lines += _block(prim, "Primary: 100 controls (shipped)")
    lines += _block(sec, "Secondary (recorded only): 300 controls")
    art = ROOT / "artifacts"
    (art / "passage_null_seeds.json").write_text(json.dumps(out, indent=1, sort_keys=True) + "\n")
    (art / "passage_null_seeds.md").write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
