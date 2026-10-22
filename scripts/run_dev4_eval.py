#!/usr/bin/env python3
"""dev4 set, report-only -> artifacts/synonym_dev4_eval.{json,md}.

Scores the shipped default and the dev4-chosen unknown-words-only Datamuse arm
(ships off: opens the must-refuse trap d4-37) on both dev4 halves, with the
must-refuse rows each arm opens. Never fails on accuracy. Exits 1 if dev4
gains a held-out word in a query or anywhere in the file (resource audit),
shares or repeats swap vocabulary, if its frozen source-grouped split moves,
or if the shipped default opens any must-refuse row.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ops_copilot.config import CopilotConfig  # noqa: E402
from ops_copilot.datamuse_dev4 import config_for, opened_must_refuse  # noqa: E402
from ops_copilot.resource_audit import audit  # noqa: E402
from ops_copilot.synonym_dev4 import half, vocabulary_problems  # noqa: E402
from ops_copilot.wordnet_dev2 import score_rows  # noqa: E402

FROZEN = {"tune": 23, "confirm": 21}
REL = "data/eval/synonym_dev4.jsonl"
DEFAULT = "default (shipped)"


def main() -> int:
    chosen = json.loads((ROOT / "artifacts" / "datamuse_dev4_confirm.json").read_text())["chosen"]
    arms = {
        DEFAULT: CopilotConfig(),
        "Datamuse unknown words only, dev4-chosen (ships off: opens d4-37)": config_for(chosen),
    }
    problems = vocabulary_problems()
    heldout_in_file = audit((REL,))[REL]
    out: dict = {"vocabulary_problems": problems, "heldout_words_in_file": heldout_in_file, "halves": {}}
    sizes, default_opened = {}, []
    for name in ("tune", "confirm"):
        rows = half(name)
        sizes[name] = len(rows)
        out["halves"][name] = {}
        for a, c in arms.items():
            s = score_rows(c, rows)
            opened = opened_must_refuse(s, rows)
            if a == DEFAULT:
                default_opened += opened
            out["halves"][name][a] = {**{k: v for k, v in s.items() if k not in ("ok", "decisions")},
                                      "must_refuse_opened": opened}
    out["split_sizes"] = sizes
    lines = ["# dev4 set (hand-written 2026-10-22, split by golden source row; report-only)", "",
             f"Vocabulary problems: {problems or 'none'}. Held-out words in file: {heldout_in_file or 'none'}. "
             f"Split sizes: {sizes}.", "",
             "| half | arm | correct | ANSWER | must-refuse opened | fail-open | spurious write | raw PII |",
             "| --- | --- | ---: | ---: | --- | ---: | ---: | ---: |"]
    for name, by_arm in out["halves"].items():
        for a, r in by_arm.items():
            lines.append(f"| {name} | {a} | {r['correct']}/{r['n']} | {r['answer_correct']}/{r['n_answer']} | "
                         f"{', '.join(r['must_refuse_opened']) or '-'} | {r['n_fail_open']} | "
                         f"{r['n_spurious_write']} | {r['n_raw_pii']} |")
    art = ROOT / "artifacts"
    (art / "synonym_dev4_eval.json").write_text(json.dumps(out, indent=1, sort_keys=True) + "\n")
    (art / "synonym_dev4_eval.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))
    return 1 if problems or heldout_in_file or sizes != FROZEN or default_opened else 0


if __name__ == "__main__":
    raise SystemExit(main())
