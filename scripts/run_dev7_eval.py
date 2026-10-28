#!/usr/bin/env python3
"""dev7 set, report-only -> artifacts/synonym_dev7_eval.{json,md}.

dev7 ``tune`` was used by the 2026-10-28 credited-word calibration and its
``confirm`` half by the one-shot confirm, so it is now a regression report for
the shipped default, per half. Never fails on accuracy. Exits 1 if dev7 gains a
held-out word, shares or repeats swap vocabulary, its frozen split moves, or
the shipped default opens any of its 13 must-refuse rows.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ops_copilot.config import CopilotConfig  # noqa: E402
from ops_copilot.datamuse_dev4 import opened_must_refuse  # noqa: E402
from ops_copilot.resource_audit import audit  # noqa: E402
from ops_copilot.synonym_dev7 import half, load_dev7, must_refuse_rows, vocabulary_problems  # noqa: E402
from ops_copilot.wordnet_dev2 import score_rows  # noqa: E402

FROZEN = {"tune": 22, "confirm": 18}
REL = "data/eval/synonym_dev7.jsonl"


def main() -> int:
    rows = load_dev7()
    problems = vocabulary_problems(rows)
    heldout_in_file = audit((REL,))[REL]
    sizes = {h: len(half(h, rows)) for h in FROZEN}
    cfg = CopilotConfig()
    out = {"vocabulary_problems": problems, "heldout_words_in_file": heldout_in_file, "split_sizes": sizes,
           "n_must_refuse": len(must_refuse_rows(rows)), "default": {}}
    lines = [
        "# dev7 set (hand-written 2026-10-28, spent by the credited-word calibration / confirm; report-only)", "",
        f"Vocabulary problems: {problems or 'none'}. Held-out words in file: {heldout_in_file or 'none'}. "
        f"Split: {sizes} ({out['n_must_refuse']} must-refuse).", "",
        "| half | correct | ANSWER | must-refuse opened | fail-open | spurious write | raw PII |",
        "| --- | ---: | ---: | --- | ---: | ---: | ---: |",
    ]
    opened_all: list[str] = []
    for h in FROZEN:
        part = half(h, rows)
        s = score_rows(cfg, part)
        opened = opened_must_refuse(s, part)
        opened_all += opened
        out["default"][h] = {**{k: v for k, v in s.items() if k != "ok"}, "must_refuse_opened": opened}
        lines.append(f"| {h} | {s['correct']}/{s['n']} | {s['answer_correct']}/{s['n_answer']} | "
                     f"{', '.join(opened) or '-'} | {s['n_fail_open']} | {s['n_spurious_write']} | {s['n_raw_pii']} |")
    art = ROOT / "artifacts"
    (art / "synonym_dev7_eval.json").write_text(json.dumps(out, indent=1, sort_keys=True) + "\n")
    (art / "synonym_dev7_eval.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))
    return 1 if problems or heldout_in_file or sizes != FROZEN or opened_all else 0


if __name__ == "__main__":
    raise SystemExit(main())
