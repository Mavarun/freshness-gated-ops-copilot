#!/usr/bin/env python3
"""Calibrate the noun gloss-sense read backoff on clean golden + dev synonyms.

Writes artifacts/noun_gloss_sense_calibration.{json,md}. Held-out rows are
never scored (see ops_copilot.noun_gloss_sense_calibration).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ops_copilot.noun_gloss_sense_calibration import calibrate  # noqa: E402


def _r(v):
    return round(v, 4) if isinstance(v, float) else v


def main() -> int:
    out = calibrate()
    chosen, base = out["chosen"], out["baseline_off"]
    compact = {
        "baseline_off": {k: _r(v) for k, v in base.items()},
        "chosen": {k: _r(v) for k, v in chosen.items()},
        "results": [{k: _r(v) for k, v in r.items()} for r in out["results"]],
        "n_safe": out["n_safe"],
        "default_on_candidate": out["default_on_candidate"],
    }
    art = ROOT / "artifacts"
    (art / "noun_gloss_sense_calibration.json").write_text(
        json.dumps(compact, indent=1) + "\n", encoding="utf-8"
    )
    lines = [
        "# Noun gloss-sense calibration (ops noun + Wiktionary all-POS bridges)",
        "",
        f"Clean golden: {chosen['n_clean']} rows. Dev synonym: {chosen['n_dev']} rows "
        "(held-out never scored). Off baseline: clean "
        f"{base['clean_accuracy']:.3f}, dev synonym {base['dev_synonym_accuracy']:.3f}.",
        "",
        f"Chosen: min_gloss_cosine **{chosen['min_gloss_cosine']}**, "
        f"max_neighbours **{chosen['max_neighbours']}**, "
        f"min_score **{chosen['min_score']}** "
        f"(clean {chosen['clean_accuracy']:.3f}, "
        f"dev synonym {chosen['dev_synonym_accuracy']:.3f}, "
        f"dev ANSWER {chosen['dev_answer_correct']}/{chosen['n_dev_answer']}; "
        f"{out['n_safe']} of {len(out['results'])} settings safe). "
        f"Calibration candidate for default-on: **{out['default_on_candidate']}**. "
        "The held-out run is the go / no-go.",
        "",
    ]
    (art / "noun_gloss_sense_calibration.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(
        f"chosen min_cos={chosen['min_gloss_cosine']} max_n={chosen['max_neighbours']} "
        f"min_score={chosen['min_score']} clean={chosen['clean_accuracy']:.3f} "
        f"dev={chosen['dev_synonym_accuracy']:.3f}; candidate={out['default_on_candidate']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
