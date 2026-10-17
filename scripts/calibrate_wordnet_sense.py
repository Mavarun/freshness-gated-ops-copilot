#!/usr/bin/env python3
"""Dev-only WordNet noun-sense calibration -> artifacts/wordnet_sense_calibration.{json,md}."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ops_copilot.wordnet_sense_calibration import calibrate  # noqa: E402


def main() -> int:
    rep = calibrate()
    art = ROOT / "artifacts"
    (art / "wordnet_sense_calibration.json").write_text(json.dumps(rep, indent=2, sort_keys=True) + "\n")
    b = rep["baseline_off"]
    lines = [
        "# WordNet noun-sense calibration (clean golden + dev synonym rows only)",
        "",
        f"Baseline (off): clean {b['clean_accuracy']:.3f}, dev synonym "
        f"{b['dev_synonym_accuracy']:.3f} ({b['dev_answer_correct']}/{b['n_dev_answer']} dev ANSWER rows).",
        "",
        "| scope | max_path | max_fanout | max_neighbours | clean | fail-open | spurious write | dev synonym | dev ANSWER | safe |",
        "| :--- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | :---: |",
    ]
    for r in rep["results"]:
        lines.append(
            f"| {r['scope']} | {r['max_path']} | {r['max_fanout']} | {r['max_neighbours']} | {r['clean_accuracy']:.3f} | "
            f"{r['n_fail_open']} | {r['n_spurious_write']} | {r['dev_synonym_accuracy']:.3f} | "
            f"{r['dev_answer_correct']}/{r['n_dev_answer']} | {'yes' if r['safe'] else 'no'} |"
        )
    c = rep["chosen"]
    lines += [
        "",
        f"Chosen (safe, then dev accuracy, then most conservative): scope {c['scope']}, max_path {c['max_path']}, "
        f"max_fanout {c['max_fanout']}, max_neighbours {c['max_neighbours']}.",
        "",
    ]
    (art / "wordnet_sense_calibration.md").write_text("\n".join(lines))
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
