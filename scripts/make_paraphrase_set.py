#!/usr/bin/env python3
"""Regenerate data/golden/paraphrase_questions.jsonl from the golden set.

Deterministic: same golden file + same --seed => byte-identical output.
tests/test_paraphrase_set.py fails if the committed file drifts.
"""

from __future__ import annotations

import argparse
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ops_copilot.eval import load_golden  # noqa: E402
from ops_copilot.paraphrase_set import (  # noqa: E402
    DEFAULT_PARAPHRASE,
    build_paraphrase_set,
    dump_jsonl,
)
from ops_copilot.perturb import DEFAULT_SEED  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--golden", default=str(ROOT / "data" / "golden" / "questions.jsonl"))
    ap.add_argument("--out", default=str(DEFAULT_PARAPHRASE))
    ap.add_argument("--seed", type=int, default=DEFAULT_SEED)
    args = ap.parse_args(argv)

    cases = load_golden(args.golden)
    rows = build_paraphrase_set(cases, seed=args.seed)
    out = dump_jsonl(rows, args.out)
    counts = Counter(r["perturbation"] for r in rows)
    print(f"golden={len(cases)} rows={len(rows)} seed={args.seed} by_type={dict(counts)}")
    print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
