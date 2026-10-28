#!/usr/bin/env python3
"""Attribute traps v3, gating CI step -> artifacts/attribute_traps_v3_eval.{json,md}.

Both halves are spent (tune in the 2026-10-28 credited-word calibration,
confirm once). Scores the shipped default and the pre-change default
(credited-word check off) on all 38. Exits non-zero if the split drifts, a
held-out word enters the file, or the shipped default opens any trap.
"""

from __future__ import annotations

import json
import sys
from dataclasses import replace
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ops_copilot.attribute_traps_v3 import FORMS, half_v3, load_traps_v3, score_traps  # noqa: E402
from ops_copilot.config import CopilotConfig  # noqa: E402
from ops_copilot.resource_audit import audit  # noqa: E402

FROZEN = {"tune": 19, "confirm": 19}
REL = "data/eval/attribute_traps_v3.jsonl"


def main() -> int:
    rows = load_traps_v3()
    sizes = {h: len(half_v3(h)) for h in FROZEN}
    heldout = audit((REL,))[REL]
    arms = {"shipped default": CopilotConfig(),
            "pre-change default (credited-word check off)": replace(CopilotConfig(), passage_support_credit_stop=False)}
    scored = {name: score_traps(cfg, rows) for name, cfg in arms.items()}
    out = {"split_sizes": sizes, "heldout_words_in_file": heldout,
           "arms": {n: {k: v for k, v in s.items() if k != "decisions"} for n, s in scored.items()}}
    art = ROOT / "artifacts"
    (art / "attribute_traps_v3_eval.json").write_text(json.dumps(out, indent=1, sort_keys=True) + "\n")
    lines = ["# Attribute traps v3 (38 must-refuse rows)", "",
             f"Split sizes: {sizes}. Held-out words in file: {heldout or 'none'}.", "",
             "| config | opened | " + " | ".join(FORMS) + " |",
             "| :--- | ---: | " + " | ".join("---:" for _ in FORMS) + " |"]
    for n, s in scored.items():
        lines.append(f"| {n} | {s['n_opened']}/{s['n']} | "
                     + " | ".join(str(s["opened_by_form"].get(f, 0)) for f in FORMS) + " |")
    lines += ["", "Opened by the shipped default: " + (", ".join(scored["shipped default"]["opened"]) or "none") + ".", ""]
    (art / "attribute_traps_v3_eval.md").write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines))
    return 1 if sizes != FROZEN or heldout or scored["shipped default"]["opened"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
