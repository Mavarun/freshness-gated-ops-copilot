#!/usr/bin/env python3
"""Post-hoc reading of the resource-agreement calibration -> artifacts/resource_agreement_posthoc.{json,md}."""

from __future__ import annotations

import dataclasses
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ops_copilot import resource_agreement_protocol as P  # noqa: E402
from ops_copilot.config import CopilotConfig  # noqa: E402
from ops_copilot.pipeline import Copilot  # noqa: E402
from ops_copilot.resource_agreement import AgreementSense  # noqa: E402
from ops_copilot.resource_agreement_posthoc import mapped_words, pair_coverage  # noqa: E402

ART = ROOT / "artifacts"
WATCH = ("restart->bounce", "latency->lag", "restart->reboot", "restart->recycle", "cadence->frequency")


def main() -> int:
    cal = json.loads((ART / "resource_agreement_calibration.json").read_text(encoding="utf-8"))
    split = json.loads((ROOT / "data/golden/synonym_split.json").read_text())
    ship = Copilot()
    texts = [f"{c.title} {c.text}" for c in ship.corpus.chunks]
    sense = AgreementSense.from_corpus(texts, scope="all", min_votes=1, max_neighbours=50)
    cov = {s: pair_coverage(sense, split[f"{s}_pairs"]) for s in ("dev", "heldout")}
    watch = {r["pair"]: r for r in cov["heldout"]["rows"] if r["pair"] in WATCH}
    gained = {}
    for arm in ("agree2_lone", "agree3_all"):
        b = Copilot(config=dataclasses.replace(CopilotConfig(), **P.ARMS[arm]))
        rows = [r for r in cal["changed_rows"][arm] if r["arm"] == "ANSWER"]
        gained[arm] = [{**r, "mapped": mapped_words(b.grounder, r["query"])} for r in rows]
    out = {"coverage": cov, "watch": watch, "gained": gained}
    (ART / "resource_agreement_posthoc.json").write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8")
    md = ["# Resource-agreement backoff, post-hoc reading (selects nothing)", "",
          "Read after the calibration picked nothing; the confirm was not run. Held-out pairs are read only because the go / no-go is decided.", "",
          "| split | single-word pairs | gold word gets >= 2 votes | >= 3 votes | top agreed (>= 2) is gold | top agreed (>= 2) is wrong |",
          "| :--- | ---: | ---: | ---: | ---: | ---: |"]
    for s, c in cov.items():
        m = c["summary"]
        md.append(f"| {s} | {m['pairs']} | {m['gold_2plus']} | {m['gold_3plus']} | {m['top2_is_gold']} | {m['top2_is_wrong']} |")
    md += ["", "Ops pairs the README names (held-out): " + "; ".join(
        f"`{p}` gold votes {r['gold_votes']}, top `{r['top']}` ({r['top_votes']})" for p, r in watch.items()), ""]
    for arm, rows in gained.items():
        md.append(f"Rows `{arm}` newly answers: " + "; ".join(
            f"{r['id']} `{r['query']}` (expect {r['expect']}; " + (", ".join(f"{m['token']} -> {'/'.join(m['alts'])}" for m in r["mapped"]) or "retrieval rewrite only") + ")"
            for r in rows))
    (ART / "resource_agreement_posthoc.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    print("\n".join(md))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
