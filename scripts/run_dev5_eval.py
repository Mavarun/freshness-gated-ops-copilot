#!/usr/bin/env python3
"""dev5 set, report-only -> artifacts/synonym_dev5_eval.{json,md}.

Scores the shipped default on the dev5 **tune** half only. The confirm half is
unspent (the 2026-10-24 calibration found no candidate), so no config is
scored on it here; only its shape is checked. Never fails on accuracy. Exits 1
if dev5 gains a held-out word in a query or anywhere in the file, shares or
repeats swap vocabulary, its frozen source-grouped split moves, or the shipped
default opens a tune must-refuse row other than the known open bug d5-38
(passage rescue ``colour <- default``, ``artifacts/passage_sense_probe.md``).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ops_copilot.config import CopilotConfig  # noqa: E402
from ops_copilot.datamuse_dev5 import opened_must_refuse  # noqa: E402
from ops_copilot.resource_audit import audit  # noqa: E402
from ops_copilot.synonym_dev5 import half, must_refuse_rows, vocabulary_problems  # noqa: E402
from ops_copilot.wordnet_dev2 import score_rows  # noqa: E402

FROZEN = {"tune": 24, "confirm": 20}
REL = "data/eval/synonym_dev5.jsonl"
# Known shipped-default fail-opens. d5-38 (passage rescue colour <- default) was
# closed on 2026-10-25 by the null-control test (artifacts/passage_null_confirm.json).
KNOWN_OPEN: tuple[str, ...] = ()


def main() -> int:
    problems = vocabulary_problems()
    heldout_in_file = audit((REL,))[REL]
    tune, confirm = half("tune"), half("confirm")
    sizes = {"tune": len(tune), "confirm": len(confirm)}
    s = score_rows(CopilotConfig(), tune)
    opened = opened_must_refuse(s, tune)
    unexpected = [r for r in opened if r not in KNOWN_OPEN]
    out = {
        "vocabulary_problems": problems,
        "heldout_words_in_file": heldout_in_file,
        "split_sizes": sizes,
        "confirm_must_refuse_rows": len(must_refuse_rows(confirm)),
        "confirm_scored": False,
        "tune_default": {**{k: v for k, v in s.items() if k not in ("ok", "decisions")},
                         "must_refuse_opened": opened},
        "known_open": list(KNOWN_OPEN),
        "unexpected_open": unexpected,
    }
    t = out["tune_default"]
    lines = [
        "# dev5 set (hand-written 2026-10-24, split by golden source row; report-only)", "",
        f"Vocabulary problems: {problems or 'none'}. Held-out words in file: {heldout_in_file or 'none'}. "
        f"Split sizes: {sizes}. The confirm half is unspent and not scored here.", "",
        "| half | arm | correct | ANSWER | must-refuse opened | fail-open | spurious write | raw PII |",
        "| --- | --- | ---: | ---: | --- | ---: | ---: | ---: |",
        f"| tune | default (shipped) | {t['correct']}/{t['n']} | {t['answer_correct']}/{t['n_answer']} | "
        f"{', '.join(opened) or '-'} | {t['n_fail_open']} | {t['n_spurious_write']} | {t['n_raw_pii']} |", "",
        f"Known open bugs: {', '.join(KNOWN_OPEN) or 'none'} (d5-38 closed 2026-10-25 by the null-control "
        f"test). Unexpected opens: {', '.join(unexpected) or 'none'}.",
    ]
    art = ROOT / "artifacts"
    (art / "synonym_dev5_eval.json").write_text(json.dumps(out, indent=1, sort_keys=True) + "\n")
    (art / "synonym_dev5_eval.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))
    return 1 if problems or heldout_in_file or sizes != FROZEN or unexpected else 0


if __name__ == "__main__":
    raise SystemExit(main())
