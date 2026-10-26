#!/usr/bin/env python3
"""dev6 set, report-only -> artifacts/synonym_dev6_eval.{json,md}.

dev6 was spent by the 2026-10-26 one-shot Datamuse confirm
(``artifacts/datamuse_dev6_confirm.json``), so it is now a regression report
for the shipped default only. Never fails on accuracy. Exits 1 if dev6 gains a
held-out word anywhere in the file, shares or repeats swap vocabulary, its row
count moves, or the shipped default opens any of its 20 must-refuse rows
(the Datamuse arm opened d6-36; the default must not).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ops_copilot.config import CopilotConfig  # noqa: E402
from ops_copilot.datamuse_dev6 import opened_must_refuse  # noqa: E402
from ops_copilot.resource_audit import audit  # noqa: E402
from ops_copilot.synonym_dev6 import load_dev6, must_refuse_rows, vocabulary_problems  # noqa: E402
from ops_copilot.wordnet_dev2 import score_rows  # noqa: E402

FROZEN_ROWS = 45
REL = "data/eval/synonym_dev6.jsonl"


def main() -> int:
    rows = load_dev6()
    problems = vocabulary_problems(rows)
    heldout_in_file = audit((REL,))[REL]
    s = score_rows(CopilotConfig(), rows)
    opened = opened_must_refuse(s, rows)
    out = {
        "vocabulary_problems": problems,
        "heldout_words_in_file": heldout_in_file,
        "n_rows": len(rows),
        "n_must_refuse": len(must_refuse_rows(rows)),
        "default": {**{k: v for k, v in s.items() if k not in ("ok", "decisions")},
                    "must_refuse_opened": opened},
    }
    d = out["default"]
    lines = [
        "# dev6 set (hand-written 2026-10-26, spent by the one-shot Datamuse confirm; report-only)", "",
        f"Vocabulary problems: {problems or 'none'}. Held-out words in file: {heldout_in_file or 'none'}. "
        f"Rows: {len(rows)} ({out['n_must_refuse']} must-refuse).", "",
        "| arm | correct | ANSWER | must-refuse opened | fail-open | spurious write | raw PII |",
        "| --- | ---: | ---: | --- | ---: | ---: | ---: |",
        f"| default (shipped) | {d['correct']}/{d['n']} | {d['answer_correct']}/{d['n_answer']} | "
        f"{', '.join(opened) or '-'} | {d['n_fail_open']} | {d['n_spurious_write']} | {d['n_raw_pii']} |",
    ]
    art = ROOT / "artifacts"
    (art / "synonym_dev6_eval.json").write_text(json.dumps(out, indent=1, sort_keys=True) + "\n")
    (art / "synonym_dev6_eval.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))
    return 1 if problems or heldout_in_file or len(rows) != FROZEN_ROWS or opened else 0


if __name__ == "__main__":
    raise SystemExit(main())
