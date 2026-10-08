#!/usr/bin/env python3
"""Calibrate the answer-support (QA translation) model on clean golden + dev rows.

Writes artifacts/answer_support_calibration.{json,md}. Needs only the committed
table (data/qa/). Held-out rows are never scored
(see ops_copilot.answer_support_calibration).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ops_copilot.answer_support_calibration import calibrate  # noqa: E402


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
    (art / "answer_support_calibration.json").write_text(
        json.dumps(compact, indent=1) + "\n", encoding="utf-8"
    )
    scope = "unknown + known words" if chosen["known_words"] else "unknown words only"
    lines = [
        "# Answer-support model calibration (QA translation, outside Stack Exchange data)",
        "",
        f"Rows: {out['n_clean']} clean golden + {out['n_dev']} dev synonym rows "
        "(no held-out rows). Default config (every backoff and embeddings off) plus the model.",
        "",
        f"Model off: accuracy {base['accuracy']:.3f} "
        f"(wrong: {', '.join(base['wrong']) or '-'}).",
        "",
        f"Chosen: lift >= **{chosen['min_score']}**, **{'strict' if chosen['strict'] else 'non-strict'}**, "
        f"scope **{scope}**, max_terms **{chosen['max_terms']}** (calibration accuracy "
        f"{chosen['accuracy']:.3f}; optimal run {chosen['optimal_run'][0]}-{chosen['optimal_run'][1]}; "
        f"{chosen['n_optimal']} of {len(out['results'])} settings tie at it). Beats model off on dev: "
        f"**{out['default_on']}** (the held-out run is the go / no-go).",
        "",
        "Per setting, the threshold range and outcome (consecutive thresholds with identical "
        "results are merged):",
        "",
        "| strictness | scope | max_terms | lift range | accuracy | clean | fail-open | spurious write | wrong |",
        "| --- | --- | ---: | --- | ---: | ---: | ---: | ---: | --- |",
    ]
    prev = None
    block: list[dict] = []

    def flush() -> None:
        if not block:
            return
        r = block[0]
        rng = f"{block[0]['min_score']}-{block[-1]['min_score']}"
        lines.append(
            f"| {_setting(r).replace(' | ', ' | ', 2)} | {rng} | {r['accuracy']:.3f} | "
            f"{r['clean_accuracy']:.3f} | {r['n_fail_open']} | {r['n_spurious_write']} | "
            f"{', '.join(r['wrong']) or '-'} |"
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
    n_model = sum(w["in_model"] for w in words)
    scored = [w for w in words if w["lift"] is not None]
    lines += [
        "",
        f"## Dev pairs, word level ({len(words)} dev replacement words)",
        "",
        f"In the model's question vocabulary: {n_model}; answered by a word of the replaced "
        f"key with any lift >= 1.0 (table floor): {len(scored)}; at the chosen "
        f"{chosen['min_score']}: {sum(w['lift'] >= chosen['min_score'] for w in scored)}.",
        "",
        "| pair | word | in model | key word | lift |",
        "| --- | --- | --- | --- | ---: |",
    ]
    for w in words:
        lines.append(
            f"| `{w['pair']}` | {w['word']} | {'yes' if w['in_model'] else 'no'} | "
            f"{w['key_word'] or '-'} | {'-' if w['lift'] is None else w['lift']} |"
        )
    (art / "answer_support_calibration.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(
        f"chosen lift>={chosen['min_score']} strict={chosen['strict']} known={chosen['known_words']} "
        f"max_terms={chosen['max_terms']} acc={chosen['accuracy']:.3f} vs off {base['accuracy']:.3f}; "
        f"default_on={out['default_on']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
