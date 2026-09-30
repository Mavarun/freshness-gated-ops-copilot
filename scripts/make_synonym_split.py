#!/usr/bin/env python3
"""Write data/golden/synonym_split.json (dev / held-out synonym pairs and rows).

Deterministic: same perturbation map + same --seed => byte-identical output.
tests/test_heldout_leakage.py fails if the committed file drifts. The
paraphrase set and golden labels are read, never rewritten.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ops_copilot.eval import load_golden  # noqa: E402
from ops_copilot.paraphrase_set import load_paraphrase_set  # noqa: E402
from ops_copilot.synonym_split import (  # noqa: E402
    DEFAULT_SPLIT_PATH,
    SPLIT_SEED,
    build_split_file,
    dump_split,
)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", default=str(DEFAULT_SPLIT_PATH))
    ap.add_argument("--seed", type=int, default=SPLIT_SEED)
    args = ap.parse_args(argv)
    split = build_split_file(load_paraphrase_set(), load_golden(), seed=args.seed)
    out = dump_split(split, args.out)
    print(
        f"words dev={len(split['dev_words'])} heldout={len(split['heldout_words'])} "
        f"pairs dev={split['n_dev_pairs']} heldout={split['n_heldout_pairs']} "
        f"rows dev={split['n_dev_rows']} heldout={split['n_heldout_rows']}"
    )
    print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
