#!/usr/bin/env python3
"""Calibrate the counter-fitted word-vector backoff on clean golden + dev rows.

Writes artifacts/word_vector_calibration.{json,md}. Needs only the committed
neighbour table (no vectors, no model). Held-out rows are never scored
(see ops_copilot.word_vector_calibration).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ops_copilot.word_vector_calibration import calibrate  # noqa: E402


def _r(v):
    return round(v, 4) if isinstance(v, float) else v


def main() -> int:
    out = calibrate()
    chosen, base = out["chosen"], out["baseline_off"]
    compact = dict(out)
    compact["results"] = [{k: _r(v) for k, v in r.items()} for r in out["results"]]
    compact["baseline_off"] = {k: _r(v) for k, v in base.items()}
    art = ROOT / "artifacts"
    (art / "word_vector_calibration.json").write_text(
        json.dumps(compact, indent=1) + "\n", encoding="utf-8"
    )
    scope = "unknown + known words" if chosen["known_words"] else "unknown words only"
    lines = [
        "# Word-vector backoff calibration (counter-fitted vectors)",
        "",
        f"Rows: {out['n_clean']} clean golden + {out['n_dev']} dev synonym rows "
        "(no held-out rows). Default config (embedding off) plus the backoff.",
        "",
        f"Backoff off: accuracy {base['accuracy']:.3f} "
        f"(wrong: {', '.join(base['wrong']) or '-'}).",
        "",
        f"Chosen: threshold **{chosen['threshold']}**, max_neighbours "
        f"**{chosen['max_neighbours']}**, scope **{scope}** (calibration accuracy "
        f"{chosen['accuracy']:.3f}; optimal run {chosen['optimal_run'][0]}-"
        f"{chosen['optimal_run'][1]}). Default on: **{out['default_on']}**.",
        "",
        "| scope | max_neighbours | threshold | accuracy | clean | fail-open | spurious write | wrong |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |",
    ]
    prev = None
    for r in out["results"]:
        sig = (r["known_words"], r["max_neighbours"], tuple(r["wrong"]))
        if sig == prev:
            continue  # print only where the outcome changes
        prev = sig
        lines.append(
            f"| {'unknown+known' if r['known_words'] else 'unknown'} | {r['max_neighbours']} | "
            f"{r['threshold']:.2f} | {r['accuracy']:.3f} | {r['clean_accuracy']:.3f} | "
            f"{r['n_fail_open']} | {r['n_spurious_write']} | {', '.join(r['wrong']) or '-'} |"
        )
    pairs = out["dev_pairs"]
    hit = sum(p["is_key_word"] for p in pairs)
    lines += [
        "",
        f"## Dev pairs, word level ({len(pairs)} dev replacement words)",
        "",
        f"Top table substitute is a content word of the replaced key: **{hit}/{len(pairs)}**; "
        f"an inflection of the word itself: {sum(p['kind'] == 'inflection' for p in pairs)}; "
        f"another word: {sum(p['kind'] == 'other' for p in pairs)} "
        f"(of which >= the chosen threshold: "
        f"{sum(p['kind'] == 'other' and p['cosine'] >= chosen['threshold'] for p in pairs)}); "
        f"nothing >= the 0.50 floor: {sum(p['kind'] == 'none' for p in pairs)}. "
        "'Another word' is not always wrong (calendar -> timeline), but several are "
        "wrong-sense substitutes (instances -> example, servicing -> service).",
        "",
        "| pair | word | top substitute | cosine | kind |",
        "| --- | --- | --- | ---: | --- |",
    ]
    for p in pairs:
        cos = f"{p['cosine']:.3f}" if p["cosine"] is not None else "-"
        lines.append(
            f"| `{p['pair']}` | {p['word']} | {p['substitute'] or '-'} | {cos} | "
            f"{p['kind']} |"
        )
    (art / "word_vector_calibration.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(
        f"baseline={base['accuracy']:.3f} chosen threshold={chosen['threshold']} "
        f"k={chosen['max_neighbours']} known={chosen['known_words']} "
        f"acc={chosen['accuracy']:.3f} run={chosen['optimal_run']} default_on={out['default_on']} "
        f"dev pairs {hit}/{len(pairs)}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
