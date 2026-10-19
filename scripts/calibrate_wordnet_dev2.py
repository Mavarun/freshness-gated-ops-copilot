#!/usr/bin/env python3
"""WordNet gate calibration on clean + dev + dev2 calib -> artifacts/wordnet_dev2_calibration.{json,md}.

Protocol (grid, safety, selection, candidate rule) is fixed in
``ops_copilot.wordnet_dev2``. Never scores held-out or dev2 confirm rows.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ops_copilot.wordnet_dev2 import calibrate  # noqa: E402


def _name(r: dict) -> str:
    rank = r["max_sense_rank"] or "all"
    return (f"{r['scope']} p{r['max_path']} f{r['max_fanout']} n{r['max_neighbours']} "
            f"morphy={'on' if r['morphy'] else 'off'} senses={rank}")


def main() -> int:
    rep = calibrate()
    art = ROOT / "artifacts"
    (art / "wordnet_dev2_calibration.json").write_text(json.dumps(rep, indent=2, sort_keys=True) + "\n")
    b = rep["baseline_off"]
    lines = [
        "# WordNet noun-sense gate: calibration on clean + dev + dev2 calib (pre-registered)",
        "",
        f"Rows: {rep['n_rows']} calibration rows (15 dev synonym + 22 dev2 calib) plus 51 clean golden; "
        f"{rep['n_settings']} settings; {rep['n_safe']} safe.",
        f"Flag off: calibration {b['correct']}/{b['n']} correct, ANSWER {b['answer_correct']}/{b['n_answer']}, "
        f"clean {b['clean']['clean_accuracy']:.3f}.",
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
    (art / "wordnet_dev2_calibration.md").write_text("\n".join(lines))
    print("\n".join(lines[:6] + lines[-3:]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
