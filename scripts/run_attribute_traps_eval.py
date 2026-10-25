#!/usr/bin/env python3
"""Attribute traps, report-only CI step -> artifacts/attribute_traps_eval.{json,md}.

Scores the shipped default and the pre-change default (null-control test off)
on all 36 attribute traps. Both halves were spent by the 2026-10-25 slice
(tune for design, confirm once), so this is now a regression guard, not a
test set. Exits non-zero if the split drifts, a held-out word enters the file,
or the shipped default opens any trap.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ops_copilot.attribute_traps import FORMS, half, load_traps, score_traps  # noqa: E402
from ops_copilot.config import CopilotConfig  # noqa: E402
from ops_copilot.passage_null_dev5 import pre_change_config  # noqa: E402
from ops_copilot.resource_audit import audit  # noqa: E402

FROZEN = {"tune": 18, "confirm": 18}
REL = "data/eval/attribute_traps.jsonl"


def main() -> int:
    rows = load_traps()
    sizes = {"tune": len(half("tune")), "confirm": len(half("confirm"))}
    heldout = audit((REL,))[REL]
    shipped, before = score_traps(CopilotConfig(), rows), score_traps(pre_change_config(), rows)
    pub = lambda s: {k: v for k, v in s.items() if k != "decisions"}  # noqa: E731
    out = {"split_sizes": sizes, "heldout_words_in_file": heldout,
           "shipped_default": pub(shipped), "pre_change_default": pub(before)}
    art = ROOT / "artifacts"
    (art / "attribute_traps_eval.json").write_text(json.dumps(out, indent=1, sort_keys=True) + "\n")
    lines = [
        "# Attribute traps (36 must-refuse rows, report-only regression guard)", "",
        f"Split sizes: {sizes}. Held-out words in file: {heldout or 'none'}.", "",
        "| config | opened | " + " | ".join(FORMS) + " |",
        "| :--- | ---: | " + " | ".join("---:" for _ in FORMS) + " |",
    ]
    for name, s in (("pre-change default (null test off)", before), ("shipped default", shipped)):
        lines.append(f"| {name} | {s['n_opened']}/{s['n']} | "
                     + " | ".join(str(s["opened_by_form"].get(f, 0)) for f in FORMS) + " |")
    lines += ["", f"Opened by the pre-change default: {', '.join(before['opened']) or 'none'}.",
              f"Opened by the shipped default: {', '.join(shipped['opened']) or 'none'}.", ""]
    (art / "attribute_traps_eval.md").write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines))
    return 1 if sizes != FROZEN or heldout or shipped["opened"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
