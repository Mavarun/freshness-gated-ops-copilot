#!/usr/bin/env python3
"""Calibrate the Stack Exchange tag-synonym backoff on clean golden + dev rows.

Writes artifacts/tag_synonym_calibration.{json,md}. Needs only the committed
snapshot (data/tagsyn/). Held-out rows are never scored
(see ops_copilot.tag_synonym_calibration).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ops_copilot.tag_synonym_calibration import calibrate  # noqa: E402


def _r(v):
    return round(v, 4) if isinstance(v, float) else v


def main() -> int:
    out = calibrate()
    chosen, base = out["chosen"], out["baseline_off"]
    compact = dict(out)
    compact["results"] = [{k: _r(v) for k, v in r.items()} for r in out["results"]]
    compact["baseline_off"] = {k: _r(v) for k, v in base.items()}
    art = ROOT / "artifacts"
    (art / "tag_synonym_calibration.json").write_text(
        json.dumps(compact, indent=1) + "\n", encoding="utf-8"
    )
    scope = "unknown + known words" if chosen["known_words"] else "unknown words only"
    lines = [
        "# Tag-synonym backoff calibration (Stack Exchange tag synonyms)",
        "",
        f"Rows: {out['n_clean']} clean golden + {out['n_dev']} dev synonym rows "
        "(no held-out rows). Default config (embedding off, word-vector backoff off) "
        "plus the backoff.",
        "",
        f"Backoff off: accuracy {base['accuracy']:.3f} "
        f"(wrong: {', '.join(base['wrong']) or '-'}).",
        "",
        f"Chosen: sites **{chosen['sites']}**, min_sites **{chosen['min_sites']}**, "
        f"max_neighbours **{chosen['max_neighbours']}**, scope **{scope}** "
        f"(calibration accuracy {chosen['accuracy']:.3f}; {chosen['n_optimal']} of "
        f"{len(out['results'])} settings tie at it). Beats backoff off on dev: "
        f"**{out['default_on']}** (the held-out run is the go / no-go).",
        "",
        "| sites | min_sites | scope | max_neighbours | accuracy | clean | fail-open | spurious write | wrong |",
        "| --- | ---: | --- | ---: | ---: | ---: | ---: | ---: | --- |",
    ]
    for r in out["results"]:
        lines.append(
            f"| {r['sites']} | {r['min_sites']} | "
            f"{'unknown+known' if r['known_words'] else 'unknown'} | {r['max_neighbours']} | "
            f"{r['accuracy']:.3f} | {r['clean_accuracy']:.3f} | {r['n_fail_open']} | "
            f"{r['n_spurious_write']} | {', '.join(r['wrong']) or '-'} |"
        )
    words = out["dev_words"]
    kinds = {k: sum(w["kind"] == k for w in words) for k in ("key", "key (not top)", "other", "none")}
    lines += [
        "",
        f"## Dev pairs, word level ({len(words)} dev replacement words)",
        "",
        f"Tag table (all sites, 1 site, top 3) offers a word of the replaced key first: "
        f"**{kinds['key']}/{len(words)}**; a key word but not first: {kinds['key (not top)']}; "
        f"only other words: {kinds['other']}; nothing: {kinds['none']}.",
        "",
        "| pair | word | substitutes | kind |",
        "| --- | --- | --- | --- |",
    ]
    for w in words:
        lines.append(
            f"| `{w['pair']}` | {w['word']} | {', '.join(w['substitutes']) or '-'} | {w['kind']} |"
        )
    (art / "tag_synonym_calibration.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(
        f"baseline={base['accuracy']:.3f} chosen={chosen} default_on={out['default_on']} "
        f"dev words key-first {kinds['key']}/{len(words)} none {kinds['none']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
