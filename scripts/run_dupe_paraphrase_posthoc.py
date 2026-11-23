#!/usr/bin/env python3
"""Post-hoc reading of the duplicate-paraphrase calibration -> artifacts/dupe_paraphrase_posthoc.{json,md}."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ops_copilot import dupe_paraphrase_protocol as P  # noqa: E402
from ops_copilot.dupe_paraphrase import DupeParaphraseSense, load_table  # noqa: E402
from ops_copilot.dupe_paraphrase_posthoc import new_swap_passes, pair_coverage  # noqa: E402
from ops_copilot.pipeline import Copilot  # noqa: E402

ART = ROOT / "artifacts"
WATCH = ("restart->bounce", "latency->lag", "restart->reboot", "restart->recycle", "cadence->frequency",
         "rotation->cycling", "schedule->timetable", "status->health")


def _knobs(arm: str) -> dict:
    a = P.ARMS[arm]
    return {"min_cross": a["dupe_min_cross"], "min_g2": a["dupe_min_g2"], "min_ratio": a["dupe_min_ratio"]}


def main() -> int:
    cal = json.loads((ART / "dupe_paraphrase_calibration.json").read_text(encoding="utf-8"))
    split = json.loads((ROOT / "data/golden/synonym_split.json").read_text())
    texts = [f"{c.title} {c.text}" for c in Copilot().corpus.chunks]
    table = load_table()
    senses = {g: DupeParaphraseSense.from_corpus(texts, table, scope="all", max_neighbours=50, **_knobs(arm))
              for g, arm in (("strict", "strict_all"), ("loose", "loose_all"))}
    cov = {s: pair_coverage(senses, table, split[f"{s}_pairs"]) for s in ("dev", "heldout")}
    watch = {r["pair"]: r for r in cov["heldout"]["rows"] if r["pair"] in WATCH}
    swaps = {arm: new_swap_passes(cal["passes"][arm], cal["passes"]["shipped"],
                                  senses["strict" if arm.startswith("strict") else "loose"])
             for arm in ("strict_known", "loose_lone", "loose_all")}
    out = {"coverage": cov, "watch": watch, "new_swap_passes": swaps}
    (ART / "dupe_paraphrase_posthoc.json").write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8")
    md = ["# Duplicate-paraphrase backoff, post-hoc reading (selects nothing)", "",
          "Read after the calibration picked nothing; the confirm was not run. Held-out pairs are read only because the go / no-go is decided.", "",
          "| split | single-word pairs | pair in table | in table, key is a corpus word | strict: gold passes | strict: top is gold | strict: top is wrong | loose: gold passes | loose: top is gold | loose: top is wrong |",
          "| :--- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |"]
    for s, c in cov.items():
        m = c["summary"]
        md.append(f"| {s} | {m['pairs']} | {m['in_table']} | {m['in_table_key_in_corpus']} | {m['strict_gold_passes']} | {m['strict_top_is_gold']} | "
                  f"{m['strict_top_is_wrong']} | {m['loose_gold_passes']} | {m['loose_top_is_gold']} | {m['loose_top_is_wrong']} |")
    md += ["", "Ops pairs the README names (held-out; table numbers G² / cross / same, then the top strict candidate):", ""]
    for p, r in watch.items():
        raw = r["raw"]
        md.append(f"- `{p}`: " + (f"G² {raw['g2']}, cross {raw['cross']}, same {raw['same']}" if raw else "not in the table")
                  + ("" if r["key_in_corpus"] else f" (`{p.split('->')[0]}` is not a corpus word)")
                  + f"; strict top `{r['strict']['top']}`, loose top `{r['loose']['top']}`")
    md.append("")
    for arm, rows in swaps.items():
        md.append(f"New random swaps answered by `{arm}` ({len(rows)}): " + "; ".join(
            f"{r['row']} `{r['term']}` -> `{r['word']}` (table maps it to `{r['mapped']}`)" for r in rows))
    (ART / "dupe_paraphrase_posthoc.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    print("\n".join(md))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
