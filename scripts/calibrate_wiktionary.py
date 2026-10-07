#!/usr/bin/env python3
"""Calibrate the Wiktionary computing-sense backoff on clean golden + dev rows.

Writes artifacts/wiktionary_calibration.{json,md}. Needs only the committed
extract (data/wiktionary/). Held-out rows are never scored.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ops_copilot.wiktionary_calibration import calibrate  # noqa: E402


def _r(v):
    return round(v, 4) if isinstance(v, float) else v


def main() -> int:
    out = calibrate()
    chosen, base = out["chosen"], out["baseline_off"]
    compact = dict(out)
    compact["results"] = [{k: _r(v) for k, v in r.items()} for r in out["results"]]
    compact["baseline_off"] = {k: _r(v) for k, v in base.items()}
    art = ROOT / "artifacts"
    (art / "wiktionary_calibration.json").write_text(
        json.dumps(compact, indent=1) + "\n", encoding="utf-8"
    )
    scope = "unknown + known words" if chosen["known_words"] else "unknown words only"
    lines = [
        "# Wiktionary computing-sense backoff calibration",
        "",
        f"Rows: {out['n_clean']} clean golden + {out['n_dev']} dev synonym rows "
        "(no held-out rows). Default config (tag synonyms, word vectors, embeddings off) "
        "plus the backoff.",
        "",
        f"Backoff off: accuracy {base['accuracy']:.3f} "
        f"(wrong: {', '.join(base['wrong']) or '-'}).",
        "",
        f"Chosen: min_score **{chosen['min_score']}**, max_neighbours "
        f"**{chosen['max_neighbours']}**, scope **{scope}** (calibration accuracy "
        f"{chosen['accuracy']:.3f}; {chosen['n_optimal']} of {len(out['results'])} settings "
        f"tie at it). Beats backoff off on dev: **{out['default_on']}** (the held-out run "
        "is the go / no-go).",
        "",
        "| min_score | scope | max_neighbours | accuracy | clean | fail-open | spurious write | wrong |",
        "| ---: | --- | ---: | ---: | ---: | ---: | ---: | --- |",
    ]
    for r in out["results"]:
        lines.append(
            f"| {r['min_score']} | {'unknown+known' if r['known_words'] else 'unknown'} | "
            f"{r['max_neighbours']} | {r['accuracy']:.3f} | {r['clean_accuracy']:.3f} | "
            f"{r['n_fail_open']} | {r['n_spurious_write']} | {', '.join(r['wrong']) or '-'} |"
        )
    words = out["dev_words"]
    kinds = {k: sum(w["kind"] == k for w in words) for k in ("key", "key (not top)", "other", "none")}
    lines += [
        "",
        f"## Dev pairs, word level ({len(words)} dev replacement words, min_score 1, top 3)",
        "",
        f"A word of the replaced key first: **{kinds['key']}/{len(words)}**; a key word but "
        f"not first: {kinds['key (not top)']}; only other words: {kinds['other']}; "
        f"nothing: {kinds['none']}.",
        "",
        "| pair | word | substitutes (score) | kind |",
        "| --- | --- | --- | --- |",
    ]
    for w in words:
        subs = ", ".join(f"{s} ({sc})" for s, sc in zip(w["substitutes"], w["scores"])) or "-"
        lines.append(f"| `{w['pair']}` | {w['word']} | {subs} | {w['kind']} |")
    (art / "wiktionary_calibration.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(
        f"baseline={base['accuracy']:.3f} chosen={chosen} default_on={out['default_on']} "
        f"dev words key-first {kinds['key']}/{len(words)} none {kinds['none']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
