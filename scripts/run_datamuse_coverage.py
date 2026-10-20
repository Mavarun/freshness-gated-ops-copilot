#!/usr/bin/env python3
"""Post-hoc Datamuse coverage of dev2 + fresh noun swaps -> artifacts/datamuse_coverage.{json,md}.

Scores dev2 and the fresh set once under flag-off and the dev2-chosen Datamuse
arm (same configs as the confirm run), buckets each single-word swap, and puts
the WordNet bucket from artifacts/wordnet_coverage.json next to it.
Diagnostic only: nothing is selected from it.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ops_copilot.config import CopilotConfig  # noqa: E402
from ops_copilot.datamuse_coverage import BUCKETS, coverage  # noqa: E402
from ops_copilot.datamuse_dev2 import config_for  # noqa: E402
from ops_copilot.datamuse_senses import DatamuseSense  # noqa: E402
from ops_copilot.fresh_synonym_eval import load_fresh, score  # noqa: E402
from ops_copilot.synonym_dev2 import load_dev2  # noqa: E402
from ops_copilot.wordnet_dev2 import score_rows  # noqa: E402


def main() -> int:
    art = ROOT / "artifacts"
    ch = json.loads((art / "datamuse_dev2_confirm.json").read_text())["chosen"]
    wn = json.loads((art / "wordnet_coverage.json").read_text())
    on_cfg, off_cfg = config_for(ch), CopilotConfig()
    d2, fresh = load_dev2(), load_fresh()
    dec = {
        "dev2": (score_rows(on_cfg, d2)["decisions"], score_rows(off_cfg, d2)["decisions"]),
        "fresh": (score(on_cfg, fresh)["decisions"], score(off_cfg, fresh)["decisions"]),
    }
    backoff = DatamuseSense(
        max_rank=ch["max_rank"], max_neighbours=ch["max_neighbours"], noun_only=ch["noun_only"],
        lone_unknown=ch["scope"] == "lone", known_only=ch["scope"] == "known",
    )
    out = {"arm": ch}
    for name, rows in (("dev2", d2), ("fresh", fresh)):
        cov = coverage(rows, dec[name][0], dec[name][1], backoff)
        for rid, v in cov["rows"].items():
            v["wordnet_bucket"] = wn[name]["rows"].get(rid, {}).get("bucket")
        wn_no_link = [rid for rid, v in cov["rows"].items() if v["wordnet_bucket"] == "no_link"]
        cov["wordnet_no_link"] = {
            "n": len(wn_no_link),
            "datamuse_rank_le_10": sum((cov["rows"][r].get("rank") or 999) <= 10 for r in wn_no_link),
            "datamuse_rank_le_100": sum(cov["rows"][r].get("rank") is not None for r in wn_no_link),
            "correct_under_arm": sum(cov["rows"][r]["bucket"] == "correct" for r in wn_no_link),
        }
        out[name] = cov
    (art / "datamuse_coverage.json").write_text(json.dumps(out, indent=2, sort_keys=True) + "\n")
    lines = ["# Datamuse coverage of noun swaps (post-hoc, dev2-chosen arm: "
             f"{ch['scope']}, rank<={ch['max_rank']}, n{ch['max_neighbours']})", "",
             "| set | single swaps | linked rank<=10 | <=20 | <=50 | <=100 | " + " | ".join(BUCKETS)
             + " | fixed without the link |",
             "| :--- |" + " ---: |" * (6 + len(BUCKETS))]
    for name in ("dev2", "fresh"):
        c, k = out[name]["counts"], out[name]["n_linked_rank_le"]
        lines.append(f"| {name} | {out[name]['n_single_swaps']} | {k[10]} | {k[20]} | {k[50]} | {k[100]} | "
                     + " | ".join(str(c[b]) for b in BUCKETS) + f" | {out[name]['n_right_without_link']} |")
    lines += ["", "Rows WordNet had no link for:", "",
              "| set | WordNet no-link rows | Datamuse link rank<=10 | rank<=100 | correct under the arm |",
              "| :--- | ---: | ---: | ---: | ---: |"]
    for name in ("dev2", "fresh"):
        w = out[name]["wordnet_no_link"]
        lines.append(f"| {name} | {w['n']} | {w['datamuse_rank_le_10']} | {w['datamuse_rank_le_100']} | "
                     f"{w['correct_under_arm']} |")
    lines += ["", "| set | row | swap | Datamuse rank | gate maps to | bucket | WordNet bucket |",
              "| :--- | :--- | :--- | ---: | :--- | :--- | :--- |"]
    for name in ("dev2", "fresh"):
        for rid, v in sorted(out[name]["rows"].items()):
            if len(v.get("pairs") or ()) != 1:
                continue
            (o, n), = v["pairs"]
            b = v["bucket"] + (" (fixed without the link)" if v.get("right_without_link") else "")
            lines.append(f"| {name} | {rid} | {o} -> {n} | {v['rank'] or '-'} | "
                         f"{', '.join(v['gate_maps_to']) or '-'} | {b} | {v['wordnet_bucket'] or '-'} |")
    (art / "datamuse_coverage.md").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
