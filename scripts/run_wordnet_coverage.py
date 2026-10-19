#!/usr/bin/env python3
"""Post-hoc WordNet coverage buckets for dev2 + fresh swap rows -> artifacts/wordnet_coverage.{json,md}.

Uses the decisions already committed in artifacts/wordnet_dev2_calibration.json
and wordnet_dev2_confirm.json (dev2) and scores the fresh set once under the
same dev2-chosen arm. Diagnostic only: nothing is selected from it.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ops_copilot.fresh_synonym_eval import load_fresh, score  # noqa: E402
from ops_copilot.synonym_dev2 import load_dev2  # noqa: E402
from ops_copilot.wordnet_coverage import BUCKETS, coverage  # noqa: E402
from ops_copilot.wordnet_dev2 import config_for, score_rows  # noqa: E402
from ops_copilot.wordnet_senses import WordNetNounSense  # noqa: E402


def main() -> int:
    art = ROOT / "artifacts"
    conf = json.loads((art / "wordnet_dev2_confirm.json").read_text())
    ch = conf["chosen"]
    # Per-setting decisions are not stored by the calibration; rescore dev2 once
    # under the chosen arm (same config, so confirm decisions are reproduced).
    d2 = load_dev2()
    decisions = score_rows(config_for(ch), d2)["decisions"]
    fresh = load_fresh()
    fresh_dec = score(config_for(ch), fresh)["decisions"]
    backoff = WordNetNounSense(
        max_path=ch["max_path"], max_fanout=ch["max_fanout"], max_neighbours=ch["max_neighbours"],
        lone_unknown=ch["scope"] == "lone", known_only=ch["scope"] == "known",
        morphy=ch["morphy"], max_sense_rank=ch["max_sense_rank"] or None,
    )
    out = {"arm": ch, "dev2": coverage(d2, decisions, backoff), "fresh": coverage(fresh, fresh_dec, backoff)}
    (art / "wordnet_coverage.json").write_text(json.dumps(out, indent=2, sort_keys=True) + "\n")
    lines = ["# WordNet coverage of missed noun swaps (post-hoc, dev2-chosen arm)", "",
             "| set | " + " | ".join(BUCKETS) + " |", "| :--- |" + " ---: |" * len(BUCKETS)]
    for name in ("dev2", "fresh"):
        c = out[name]["counts"]
        lines.append(f"| {name} | " + " | ".join(str(c[b]) for b in BUCKETS) + " |")
    lines += ["", "| set | row | swap | bucket | WordNet link (path, relation, sense rank) |",
              "| :--- | :--- | :--- | :--- | :--- |"]
    for name in ("dev2", "fresh"):
        for rid, v in sorted(out[name]["rows"].items()):
            if v["bucket"] in ("correct", "not_applicable"):
                continue
            lk = v.get("link")
            lks = f"{lk['path']}, {lk['relation']}, {lk['sense_rank']}" if lk else "-"
            sw = ", ".join(f"{o} -> {n}" for o, n in v["pairs"])
            lines.append(f"| {name} | {rid} | {sw} | {v['bucket']} | {lks} |")
    (art / "wordnet_coverage.md").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
