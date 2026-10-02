#!/usr/bin/env python3
"""Calibrate semantic_grounding_threshold on clean golden + dev synonym rows.

Writes artifacts/semantic_grounding_calibration.{json,md}. Uses the frozen
embedding fixture, so it runs without the model. Held-out rows are never
scored (see ops_copilot.semantic_calibration).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ops_copilot.semantic_calibration import calibrate  # noqa: E402


def main() -> int:
    out = calibrate()
    chosen = out["chosen"]
    compact = dict(out)
    compact["results"] = [
        {k: (round(v, 4) if isinstance(v, float) else v) for k, v in r.items()}
        for r in out["results"]
    ]
    art = ROOT / "artifacts"
    (art / "semantic_grounding_calibration.json").write_text(
        json.dumps(compact, indent=1) + "\n", encoding="utf-8"
    )
    lines = [
        "# Semantic grounding threshold calibration",
        "",
        f"Rows: {out['n_clean']} clean golden + {out['n_dev']} dev synonym rows "
        "(no held-out rows). Frozen MiniLM fixture; dense retriever and grounding "
        "backoff both on.",
        "",
        f"Chosen: threshold **{chosen['threshold']}**, max_terms **{chosen['max_terms']}** "
        f"(calibration accuracy {chosen['accuracy']:.3f}; optimal run "
        f"{chosen['optimal_run'][0]}-{chosen['optimal_run'][1]}).",
        "",
        "| threshold | max_terms | accuracy | clean | fail-open | spurious write | wrong |",
        "| ---: | ---: | ---: | ---: | ---: | ---: | --- |",
    ]
    prev = None
    for r in out["results"]:
        sig = (r["max_terms"], tuple(r["wrong"]))
        if sig == prev:
            continue  # print only where the outcome changes
        prev = sig
        lines.append(
            f"| {r['threshold']:.3f} | {r['max_terms']} | {r['accuracy']:.3f} | "
            f"{r['clean_accuracy']:.3f} | {r['n_fail_open']} | {r['n_spurious_write']} | "
            f"{', '.join(r['wrong']) or '-'} |"
        )
    (art / "semantic_grounding_calibration.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"chosen threshold={chosen['threshold']} max_terms={chosen['max_terms']} "
          f"acc={chosen['accuracy']:.3f} run={chosen['optimal_run']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
