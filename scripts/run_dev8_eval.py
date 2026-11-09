#!/usr/bin/env python3
"""dev8 set on the shipped default (CI step) -> artifacts/dev8_eval.{json,md}.

dev8 was spent on 2026-11-09 by the one-shot non-key coverage confirm, so this is a
regression guard, not a test set. Gating on safety: exits non-zero if a held-out word
enters the file, the row count moves, or the shipped default opens a dev8 topic trap
outside the five it opened at the confirm (KNOWN_OPEN). Accuracy on the 32 wordy rows
is report-only. The off-by-default non-key rule ('all') is scored alongside.
"""

from __future__ import annotations

import dataclasses
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ops_copilot import nonkey_coverage_protocol as P  # noqa: E402
from ops_copilot.config import CopilotConfig  # noqa: E402
from ops_copilot.pipeline import Copilot  # noqa: E402
from ops_copilot.resource_audit import audit  # noqa: E402
from ops_copilot.swap_null import file_rows  # noqa: E402

ART = ROOT / "artifacts"
KNOWN_OPEN = ("d8-t02", "d8-t03", "d8-t05", "d8-t08", "d8-t12")


def main() -> int:
    rows = file_rows((P.DEV8_FILE,))
    heldout = audit((P.DEV8_FILE,))[P.DEV8_FILE]
    bots = {"shipped": Copilot(), "all (off)": Copilot(config=dataclasses.replace(CopilotConfig(), **P.ARMS["all"]))}
    res: dict[str, dict] = {}
    for n, b in bots.items():
        dec = {r.id: b.ask(r.query).decision.value for r in rows}
        res[n] = {"answered": sum(dec[r.id] == "ANSWER" for r in rows if r.expect == "ANSWER"),
                  "traps_open": [r.id for r in rows if r.expect != "ANSWER" and dec[r.id] == "ANSWER"],
                  "decisions": dec}
    problems = []
    if heldout:
        problems.append(f"held-out words in file: {heldout}")
    if len(rows) != 48:
        problems.append(f"row count {len(rows)} != 48")
    new = sorted(set(res["shipped"]["traps_open"]) - set(KNOWN_OPEN))
    if new:
        problems.append(f"shipped default opens new topic traps: {new}")
    out = {"rows": len(rows), "heldout_words_in_file": heldout, "known_open": list(KNOWN_OPEN),
           "arms": res, "problems": problems}
    (ART / "dev8_eval.json").write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8")
    md = ["# dev8 (spent 2026-11-09): wordy questions and topic traps", "",
          "| arm | wordy rows answered (32) | topic traps open (16) |", "| :--- | ---: | :--- |",
          *[f"| `{n}` | {d['answered']} | {len(d['traps_open'])} {', '.join(d['traps_open'])} |" for n, d in res.items()],
          "", "Problems: " + ("; ".join(problems) if problems else "none")]
    (ART / "dev8_eval.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    print("\n".join(md))
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
