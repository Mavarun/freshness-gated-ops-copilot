#!/usr/bin/env python3
"""Context-gated Datamuse calibration -> artifacts/datamuse_dev3_calibration.{json,md}.

Protocol fixed in ``ops_copilot.datamuse_dev3``. Rows: dev synonym + all dev2
+ dev3 calib, plus clean golden. Never scores held-out or dev3 confirm rows.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ops_copilot.datamuse_dev3 import calibrate  # noqa: E402


def _name(r: dict) -> str:
    return f"{r['scope']} rank<={r['max_rank']} n{r['max_neighbours']} context>={r['context_min']}"


def main() -> int:
    rep = calibrate()
    art = ROOT / "artifacts"
    (art / "datamuse_dev3_calibration.json").write_text(json.dumps(rep, indent=2, sort_keys=True) + "\n")
    b = rep["baseline_off"]
    by = rep["rows_by_set"]
    lines = [
        "# Context-gated Datamuse: calibration on dev + dev2 + dev3 calib (pre-registered)",
        "",
        f"Rows: {rep['n_rows']} calibration rows ({by['dev']} dev synonym, {by['dev2']} dev2, "
        f"{by['dev3_calib']} dev3 calib) plus 51 clean golden; {rep['n_settings']} settings; {rep['n_safe']} safe.",
        f"Flag off: calibration {b['correct']}/{b['n']} correct, ANSWER {b['answer_correct']}/{b['n_answer']}, "
        f"clean {b['clean']['clean_accuracy']:.3f}. context>=0 means the gate is off.",
        "",
        "| setting | clean | calib correct | calib ANSWER | fail-open | spurious write | new errors | fixed | safe |",
        "| :--- | ---: | ---: | ---: | ---: | ---: | :--- | :--- | :---: |",
    ]
    for r in rep["results"]:
        lines.append(
            f"| {_name(r)} | {r['clean_accuracy']:.3f} | {r['calib_correct']}/{rep['n_rows']} | "
            f"{r['calib_answer_correct']}/{b['n_answer']} | {r['n_fail_open']} | {r['n_spurious_write']} | "
            f"{', '.join(r['new_errors']) or '-'} | {', '.join(r['fixed']) or '-'} | {'yes' if r['safe'] else 'no'} |"
        )
    c = rep["chosen"]
    lines += [
        "",
        f"Chosen: {_name(c)} ({c['calib_correct']}/{rep['n_rows']}; off {b['correct']}/{b['n']}). "
        f"Candidate for the confirm run: {'yes' if rep['candidate'] else 'no'}.",
        "",
    ]
    (art / "datamuse_dev3_calibration.md").write_text("\n".join(lines))
    print("\n".join(lines[:6] + lines[-3:]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
