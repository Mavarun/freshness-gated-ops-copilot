#!/usr/bin/env python3
"""Calibrate the gloss-sense write backoff on clean golden + hand-written verbs.

Writes artifacts/gloss_sense_calibration.{json,md}. Held-out rows are never
scored (see ops_copilot.gloss_sense_calibration).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ops_copilot.gloss_sense_calibration import calibrate  # noqa: E402


def _r(v):
    return round(v, 4) if isinstance(v, float) else v


def main() -> int:
    out = calibrate()
    chosen, base = out["chosen"], out["baseline_off"]
    compact = {
        "baseline_off": {k: _r(v) for k, v in base.items()},
        "chosen": {
            k: (_r(v) if k != "per_row" else v) for k, v in chosen.items()
        },
        "results": [{k: _r(v) for k, v in r.items()} for r in out["results"]],
        "n_safe": out["n_safe"],
        "default_on_candidate": out["default_on_candidate"],
    }
    art = ROOT / "artifacts"
    (art / "gloss_sense_calibration.json").write_text(
        json.dumps(compact, indent=1) + "\n", encoding="utf-8"
    )
    lines = [
        "# Gloss-sense calibration (Wiktionary computing verb gloss bridges)",
        "",
        f"Clean golden: {chosen['n_clean']} rows via ``run_eval``. Verb list: "
        f"{chosen['n_verbs']} hand-written verbs in ``data/write/gloss_sense_dev.jsonl`` "
        "(no ontology verbs, no held-out words). Held-out synonym rows are not scored.",
        "",
        f"Backoff off: clean {base['clean_accuracy']:.3f}, verb-list accuracy "
        f"{base['verb_accuracy']:.3f} (every verb predicted ``none``).",
        "",
        f"Chosen: min_score **{chosen['min_score']}**, margin **{chosen['margin']}**, "
        f"min_gloss_cosine **{chosen['min_gloss_cosine']}** "
        f"(clean {chosen['clean_accuracy']:.3f}, verb-list {chosen['verb_accuracy']:.3f}; "
        f"{out['n_safe']} of {len(out['results'])} settings clear the safety bar). "
        f"Calibration candidate for default-on: **{out['default_on_candidate']}**. "
        "The held-out run is the go / no-go.",
        "",
        "## Verb list (chosen setting)",
        "",
        "| verb | kind | label | predicted | score | ok |",
        "| --- | --- | --- | --- | ---: | --- |",
    ]
    for r in chosen["per_row"]:
        lines.append(
            f"| {r['verb']} | {r['kind']} | {r['label']} | {r['predicted']} | "
            f"{'-' if r['score'] is None else r['score']} | {'yes' if r['ok'] else 'no'} |"
        )
    (art / "gloss_sense_calibration.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(
        f"chosen min_score={chosen['min_score']} margin={chosen['margin']} "
        f"min_cos={chosen['min_gloss_cosine']} verb_acc={chosen['verb_accuracy']:.3f} "
        f"clean={chosen['clean_accuracy']:.3f}; candidate={out['default_on_candidate']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
