#!/usr/bin/env python3
"""Calibrate the passage-level answer-support backoff on clean golden + dev rows.

Writes artifacts/passage_support_calibration.{json,md}. Needs only the
committed classifier and vectors (data/domainvec/). Held-out rows are never
scored (see ops_copilot.passage_support_calibration).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ops_copilot.passage_support_calibration import calibrate  # noqa: E402


def _r(v):
    return round(v, 4) if isinstance(v, float) else v


def _setting(r: dict) -> str:
    scope = "unknown+known" if r["known_words"] else "unknown"
    return f"{'strict' if r['strict'] else 'non-strict'} | {scope} | {r['max_terms']}"


def main() -> int:
    out = calibrate()
    chosen, base = out["chosen"], out["baseline_off"]
    compact = dict(out)
    compact["results"] = [{k: _r(v) for k, v in r.items()} for r in out["results"]]
    compact["baseline_off"] = {k: _r(v) for k, v in base.items()}
    art = ROOT / "artifacts"
    (art / "passage_support_calibration.json").write_text(json.dumps(compact, indent=1) + "\n", encoding="utf-8")
    scope = "unknown + known words" if chosen["known_words"] else "unknown words only"
    lines = [
        "# Passage-level answer-support calibration (outside Stack Exchange pairs + domain vectors)",
        "",
        f"Rows: {out['n_clean']} clean golden + {out['n_dev']} dev synonym rows "
        "(no held-out rows). Default config (every backoff and embeddings off) plus the classifier.",
        "",
        f"Classifier off: accuracy {base['accuracy']:.3f} (wrong: {', '.join(base['wrong']) or '-'}).",
        "",
        f"Chosen: P(answers) >= **{chosen['min_prob']}**, **{'strict' if chosen['strict'] else 'non-strict'}**, "
        f"scope **{scope}**, max_terms **{chosen['max_terms']}** (calibration accuracy "
        f"{chosen['accuracy']:.3f}; optimal run {chosen['optimal_run'][0]}-{chosen['optimal_run'][1]}; "
        f"{chosen['n_optimal']} of {len(out['results'])} settings tie at it). Beats classifier off on dev: "
        f"**{out['default_on']}** (the held-out run is the go / no-go).",
        "",
        "Per setting, the threshold range and outcome (consecutive thresholds with identical results are merged):",
        "",
        "| strictness | scope | max_terms | P range | accuracy | clean | fail-open | spurious write | wrong |",
        "| --- | --- | ---: | --- | ---: | ---: | ---: | ---: | --- |",
    ]
    prev = None
    block: list[dict] = []

    def flush() -> None:
        if not block:
            return
        r = block[0]
        rng = f"{block[0]['min_prob']}-{block[-1]['min_prob']}"
        lines.append(
            f"| {_setting(r)} | {rng} | {r['accuracy']:.3f} | {r['clean_accuracy']:.3f} | {r['n_fail_open']} | "
            f"{r['n_spurious_write']} | {', '.join(r['wrong']) or '-'} |"
        )

    for r in out["results"]:
        key = (_setting(r), r["accuracy"], r["clean_accuracy"], tuple(r["wrong"]))
        if key != prev:
            flush()
            block = []
            prev = key
        block.append(r)
    flush()
    words = out["dev_words"]
    scored = [w for w in words if w["cosine"] is not None]
    lines += [
        "",
        f"## Dev pairs, word level ({len(words)} dev replacement words)",
        "",
        f"In the domain vectors: {sum(w['in_vectors'] for w in words)}; with a cosine to a word of the "
        f"replaced key: {len(scored)}; cosine >= 0.5: {sum(w['cosine'] >= 0.5 for w in scored)}.",
        "",
        "| pair | word | in vectors | key word | cosine |",
        "| --- | --- | --- | --- | ---: |",
    ]
    for w in words:
        lines.append(
            f"| `{w['pair']}` | {w['word']} | {'yes' if w['in_vectors'] else 'no'} | "
            f"{w['key_word'] or '-'} | {'-' if w['cosine'] is None else w['cosine']} |"
        )
    (art / "passage_support_calibration.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(
        f"chosen P>={chosen['min_prob']} strict={chosen['strict']} known={chosen['known_words']} "
        f"max_terms={chosen['max_terms']} acc={chosen['accuracy']:.3f} vs off {base['accuracy']:.3f}; "
        f"default_on={out['default_on']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
