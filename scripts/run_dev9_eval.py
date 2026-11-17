#!/usr/bin/env python3
"""dev9 set on the shipped default (CI step) -> artifacts/dev9_eval.{json,md}.

dev9 was spent on 2026-11-17 by the one-shot citation-aware non-key confirm, so this is a
regression guard, not a test set. Gating on safety: exits non-zero if a held-out word
enters the file, the row count moves, the shipped default opens any of the 16 topic
traps (it opened none at the confirm), answers a wordy row from evidence outside the
row's hand-written doc list (``data/eval/nonkey_dev9_docs.json``), or answers fewer than
SHIPPED_MIN_ANSWERED of the 32 wordy rows (12, the confirm value). The rule-off default
(up to 2026-11-16) is scored alongside and must reproduce the confirm's shipped arm
(13 rows, trap d9-t02 open).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ops_copilot import nonkey_citation_protocol as P  # noqa: E402
from ops_copilot.citation_keep import load_dev9_docs  # noqa: E402
from ops_copilot.config import pre_nonkey_config  # noqa: E402
from ops_copilot.pipeline import Copilot  # noqa: E402
from ops_copilot.resource_audit import audit  # noqa: E402

ART = ROOT / "artifacts"
KNOWN_OPEN: tuple[str, ...] = ()
SHIPPED_MIN_ANSWERED = 12
PRE = "rule off (pre-Nov 17)"
PRE_ANSWERED, PRE_OPEN = 13, ("d9-t02",)


def main() -> int:
    rows = [json.loads(x) for x in (ROOT / P.DEV9_FILE).read_text(encoding="utf-8").splitlines() if x.strip()]
    labels = load_dev9_docs()
    heldout = audit((P.DEV9_FILE,))[P.DEV9_FILE]
    bots = {"shipped": Copilot(), PRE: Copilot(config=pre_nonkey_config())}
    res: dict[str, dict] = {}
    for n, b in bots.items():
        out = {r["id"]: b.ask(r["query"]) for r in rows}
        wordy = [r for r in rows if r["expect_decision"] == "ANSWER"]
        answered = [r["id"] for r in wordy if out[r["id"]].decision.value == "ANSWER"]
        res[n] = {
            "answered": len(answered),
            "wrong_evidence": [i for i in answered if not set(out[i].cited_ids) & labels[i]],
            "traps_open": [r["id"] for r in rows if r["expect_decision"] != "ANSWER" and out[r["id"]].decision.value == "ANSWER"],
            "decisions": {i: o.decision.value for i, o in out.items()},
        }
    problems = []
    if heldout:
        problems.append(f"held-out words in file: {heldout}")
    if len(rows) != 48:
        problems.append(f"row count {len(rows)} != 48")
    sh = res["shipped"]
    if sorted(set(sh["traps_open"]) - set(KNOWN_OPEN)):
        problems.append(f"shipped default opens topic traps: {sh['traps_open']}")
    if sh["wrong_evidence"]:
        problems.append(f"shipped default answers from the wrong evidence: {sh['wrong_evidence']}")
    if sh["answered"] < SHIPPED_MIN_ANSWERED:
        problems.append(f"shipped default answers {sh['answered']} < {SHIPPED_MIN_ANSWERED} wordy rows")
    if res[PRE]["answered"] != PRE_ANSWERED or tuple(res[PRE]["traps_open"]) != PRE_OPEN:
        problems.append(f"rule-off default no longer reproduces the confirm: {res[PRE]['answered']} {res[PRE]['traps_open']}")
    out = {"rows": len(rows), "heldout_words_in_file": heldout, "known_open": list(KNOWN_OPEN),
           "arms": res, "problems": problems}
    (ART / "dev9_eval.json").write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8")
    md = ["# dev9 (spent 2026-11-17): wordy questions and topic traps", "",
          "| arm | wordy rows answered (32) | answered from wrong evidence | topic traps open (16) |",
          "| :--- | ---: | :--- | :--- |",
          *[f"| `{n}` | {d['answered']} | {' '.join([str(len(d['wrong_evidence'])), *d['wrong_evidence']])} | "
            f"{' '.join([str(len(d['traps_open'])), *d['traps_open']])} |" for n, d in res.items()],
          "", "Problems: " + ("; ".join(problems) if problems else "none")]
    (ART / "dev9_eval.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    print("\n".join(md))
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
