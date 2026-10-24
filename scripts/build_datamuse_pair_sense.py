#!/usr/bin/env python3
"""Build data/datamuse/cf_pair_cosine.json.gz (counter-fitted cosine per Datamuse pair).

    curl -L -o /tmp/cfv.zip \\
      https://github.com/nmrksic/counter-fitting/raw/master/word_vectors/counter-fitted-vectors.txt.zip
    python scripts/build_datamuse_pair_sense.py --source /tmp/cfv.zip

Only pairs already in data/datamuse/ml_neighbours.json.gz are scored, so the
output depends on the Datamuse snapshot (corpus-word queries) and the vectors.
"""

from __future__ import annotations

import argparse
import hashlib
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from build_word_neighbours import _lines  # noqa: E402

from ops_copilot.datamuse_pair_sense import DEFAULT_TABLE, SCALE, build_pair_table, dump_table  # noqa: E402
from ops_copilot.datamuse_senses import load_table  # noqa: E402
from ops_copilot.word_vectors import SOURCE_NAME, SOURCE_SHA256, SOURCE_URL, read_text_vectors  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--source", type=Path, required=True)
    ap.add_argument("--out", type=Path, default=DEFAULT_TABLE)
    ap.add_argument("--allow-other-source", action="store_true")
    args = ap.parse_args(argv)
    sha = hashlib.sha256(args.source.read_bytes()).hexdigest()
    if sha != SOURCE_SHA256 and not args.allow_other_source:
        print(f"source SHA-256 {sha} != expected {SOURCE_SHA256}", file=sys.stderr)
        return 2
    dm = load_table()
    words, vecs = read_text_vectors(_lines(args.source))
    table = build_pair_table(dm.neighbours, words, vecs)
    n_pairs = sum(len(v) for v in table.values())
    n_missing = sum(x is None for v in table.values() for x in v)
    meta = {
        "source": SOURCE_NAME,
        "source_url": SOURCE_URL,
        "source_sha256": sha,
        "license": "Apache-2.0 (github.com/nmrksic/counter-fitting)",
        "datamuse_raw_sha256": dm.meta.get("raw_sha256"),
        "datamuse_corpus_fingerprint": dm.meta.get("corpus_fingerprint"),
        "scale": SCALE,
        "n_keys": len(table),
        "n_pairs": n_pairs,
        "n_missing": n_missing,
    }
    dump_table(table, meta, args.out)
    print(f"wrote {args.out} ({args.out.stat().st_size} bytes): {len(table)} keys, {n_pairs} pairs, {n_missing} OOV")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
