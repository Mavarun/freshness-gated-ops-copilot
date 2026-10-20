#!/usr/bin/env python3
"""dev2 calibration set, report-only -> artifacts/synonym_dev2_eval.{json,md}.

Scores the shipped default config and the dev2-chosen WordNet and Datamuse
arms (both ship off) on both halves of ``data/eval/synonym_dev2.jsonl``, so later
slices start from a recorded baseline. Never fails on accuracy. Exits 1 if
the set gains a held-out word or shares swap vocabulary with the other sets
(``synonym_dev2.vocabulary_problems``), or if the frozen split moves.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ops_copilot.config import CopilotConfig  # noqa: E402
from ops_copilot.synonym_dev2 import half, vocabulary_problems  # noqa: E402
from ops_copilot.datamuse_dev2 import config_for as datamuse_config  # noqa: E402
from ops_copilot.wordnet_dev2 import config_for, score_rows  # noqa: E402

FROZEN = {"calib": 22, "confirm": 21}


def main() -> int:
    chosen = json.loads((ROOT / "artifacts" / "wordnet_dev2_confirm.json").read_text())["chosen"]
    dm = json.loads((ROOT / "artifacts" / "datamuse_dev2_confirm.json").read_text())["chosen"]
    arms = {
        "default (shipped)": CopilotConfig(),
        "WordNet, dev2-chosen (ships off)": config_for(chosen),
        "Datamuse means-like, dev2-chosen (ships off)": datamuse_config(dm),
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
    lines = ["# dev2 calibration set (hand-written 2026-10-19, report-only)", "",
             f"Vocabulary problems: {problems or 'none'}. Split sizes: {sizes}.", "",
             "| half | arm | correct | ANSWER | fail-open | spurious write | raw PII |",
             "| --- | --- | ---: | ---: | ---: | ---: | ---: |"]
    for name, by_arm in out["halves"].items():
        for a, r in by_arm.items():
            lines.append(f"| {name} | {a} | {r['correct']}/{r['n']} | {r['answer_correct']}/{r['n_answer']} | "
                         f"{r['n_fail_open']} | {r['n_spurious_write']} | {r['n_raw_pii']} |")
    art = ROOT / "artifacts"
    (art / "synonym_dev2_eval.json").write_text(json.dumps(out, indent=1, sort_keys=True) + "\n")
    (art / "synonym_dev2_eval.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))
    return 1 if problems or sizes != FROZEN else 0


if __name__ == "__main__":
    raise SystemExit(main())
