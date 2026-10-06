#!/usr/bin/env python3
"""Fresh hand-written general-English synonym set -> artifacts/synonym_fresh_eval.{json,md}.

Report-only (never fails on accuracy). Exits 1 if a swapped-in word overlaps
the perturbation split / synonym map vocabulary, because then the set would
no longer be separate from the 203-row eval.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ops_copilot.fresh_synonym_eval import load_fresh, run_fresh_eval  # noqa: E402


def main() -> int:
    out = run_fresh_eval()
    rows = {r["id"]: r for r in load_fresh()}
    art = ROOT / "artifacts"
    (art / "synonym_fresh_eval.json").write_text(json.dumps(out, indent=1, sort_keys=True) + "\n")
    labels = list(out["configs"])
    lines = [
        "# Fresh general-English synonym set (hand-written, separate from the 203 rows)",
        "",
        f"{out['n_rows']} rows in `data/eval/synonym_fresh.jsonl`: golden queries with one or two "
        "general-English swaps, golden labels kept. Written by the backoff's author after it was "
        "calibrated, so this is a check of what the resource is for, not a blind benchmark. "
        f"Vocabulary overlap with the perturbation split / synonym map: "
        f"{out['vocabulary_overlap'] or 'none'}.",
        "",
        "| config | accuracy | ANSWER rows correct | fail-open | spurious write | raw PII |",
        "| --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for label, r in out["configs"].items():
        ok = r["n"] - len(r["wrong"])
        lines.append(
            f"| {label} | {ok}/{r['n']} ({r['accuracy']:.3f}) | {r['answer_correct']} | "
            f"{r['n_fail_open']} | {r['n_spurious_write']} | {r['n_raw_pii_outputs']} |"
        )
    lines += ["", "| row | swap | expected | " + " | ".join(labels) + " |",
              "| --- | --- | --- | " + " | ".join("---" for _ in labels) + " |"]
    for rid, row in rows.items():
        cells = []
        for label in labels:
            got = out["configs"][label]["decisions"][rid]
            cells.append(("**ok**" if got == row["expect_decision"] else got))
        lines.append(f"| {rid} | {row['swap']} | {row['expect_decision']} | " + " | ".join(cells) + " |")
    (art / "synonym_fresh_eval.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    for label, r in out["configs"].items():
        print(f"{label:48s} acc={r['accuracy']:.3f} answer={r['answer_correct']} fail_open={r['n_fail_open']}")
    return 1 if out["vocabulary_overlap"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
