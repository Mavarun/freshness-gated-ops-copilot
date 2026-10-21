#!/usr/bin/env python3
"""dev3 set, report-only -> artifacts/synonym_dev3_eval.{json,md}.

Scores the shipped default and the two context-gated Datamuse arms that ship
off (dev3-chosen; same with unknown words only) on both dev3 halves. Never
fails on accuracy. Exits 1 if dev3 gains a held-out word or shares / repeats
swap vocabulary (``synonym_dev3.vocabulary_problems``), or if its frozen
source-grouped split moves.
"""

from __future__ import annotations

import json
import sys
from dataclasses import replace
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ops_copilot.config import CopilotConfig  # noqa: E402
from ops_copilot.datamuse_dev3 import config_for  # noqa: E402
from ops_copilot.synonym_dev3 import half, vocabulary_problems  # noqa: E402
from ops_copilot.wordnet_dev2 import score_rows  # noqa: E402

FROZEN = {"calib": 25, "confirm": 20}


def main() -> int:
    chosen = json.loads((ROOT / "artifacts" / "datamuse_dev3_confirm.json").read_text())["chosen"]
    arms = {
        "default (shipped)": CopilotConfig(),
        "Datamuse context-gated, dev3-chosen (ships off: opens a unit-test trap)": config_for(chosen),
        "same, unknown words only (post-hoc, ships off)": replace(config_for(chosen), datamuse_expand_known=False),
    }
    problems = vocabulary_problems()
    out: dict = {"vocabulary_problems": problems, "halves": {}}
    sizes = {}
    for name in ("calib", "confirm"):
        rows = half(name)
        sizes[name] = len(rows)
        out["halves"][name] = {a: {k: v for k, v in score_rows(c, rows).items() if k != "ok"}
                               for a, c in arms.items()}
    out["split_sizes"] = sizes
    lines = ["# dev3 set (hand-written 2026-10-21, split by golden source row; report-only)", "",
             f"Vocabulary problems: {problems or 'none'}. Split sizes: {sizes}.", "",
             "| half | arm | correct | ANSWER | fail-open | spurious write | raw PII |",
             "| --- | --- | ---: | ---: | ---: | ---: | ---: |"]
    for name, by_arm in out["halves"].items():
        for a, r in by_arm.items():
            lines.append(f"| {name} | {a} | {r['correct']}/{r['n']} | {r['answer_correct']}/{r['n_answer']} | "
                         f"{r['n_fail_open']} | {r['n_spurious_write']} | {r['n_raw_pii']} |")
    art = ROOT / "artifacts"
    (art / "synonym_dev3_eval.json").write_text(json.dumps(out, indent=1, sort_keys=True) + "\n")
    (art / "synonym_dev3_eval.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))
    return 1 if problems or sizes != FROZEN else 0


if __name__ == "__main__":
    raise SystemExit(main())
