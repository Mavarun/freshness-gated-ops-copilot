#!/usr/bin/env python3
"""Build data/wordvec/cf_neighbours.json.gz from the counter-fitted vectors.

Run locally once (CI only reads the committed table):

    curl -L -o /tmp/cfv.zip \\
      https://github.com/nmrksic/counter-fitting/raw/master/word_vectors/counter-fitted-vectors.txt.zip
    python scripts/build_word_neighbours.py --source /tmp/cfv.zip

The archive's SHA-256 is checked against ``EXPECTED_SHA256`` (the file this
table was built from) unless ``--allow-other-source`` is given. The table maps
*every* source word (no eval-driven filtering) onto its nearest corpus content
words with cosine >= the floor, so its contents depend only on the external
vectors and the corpus. The source vectors are Apache-2.0
(github.com/nmrksic/counter-fitting).
"""

from __future__ import annotations

import argparse
import hashlib
import io
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ops_copilot.corpus import Corpus  # noqa: E402
from ops_copilot.word_vectors import (  # noqa: E402
    DEFAULT_TABLE,
    SOURCE_NAME,
    SOURCE_SHA256,
    SOURCE_URL,
    TABLE_FLOOR,
    TABLE_TOP_K,
    build_neighbour_table,
    corpus_words,
    dump_table,
    read_text_vectors,
    words_fingerprint,
)

EXPECTED_SHA256 = SOURCE_SHA256


def _lines(path: Path):
    if path.suffix == ".zip":
        with zipfile.ZipFile(path) as zf:
            name = next(n for n in zf.namelist() if n.endswith(".txt"))
            with zf.open(name) as fh:
                yield from io.TextIOWrapper(fh, encoding="utf-8")
    else:
        with path.open(encoding="utf-8") as fh:
            yield from fh


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--source", required=True, help="counter-fitted-vectors.txt(.zip)")
    ap.add_argument("--out", default=str(DEFAULT_TABLE))
    ap.add_argument("--floor", type=float, default=TABLE_FLOOR)
    ap.add_argument("--top-k", type=int, default=TABLE_TOP_K)
    ap.add_argument("--allow-other-source", action="store_true")
    args = ap.parse_args(argv)

    src = Path(args.source)
    digest = hashlib.sha256(src.read_bytes()).hexdigest()
    if src.suffix == ".zip" and digest != EXPECTED_SHA256 and not args.allow_other_source:
        raise SystemExit(f"unexpected source sha256 {digest} (want {EXPECTED_SHA256})")
    words, vectors = read_text_vectors(_lines(src))
    corpus = Corpus()
    targets = corpus_words(f"{c.title} {c.text}" for c in corpus.chunks)
    reachable = [t for t in targets if t in set(words)]
    table = build_neighbour_table(words, vectors, targets, floor=args.floor, top_k=args.top_k)
    meta = {
        "source": SOURCE_NAME,
        "source_url": SOURCE_URL,
        "source_sha256": digest,
        "source_license": "Apache-2.0",
        "n_source_words": len(words),
        "dim": int(vectors.shape[1]) if vectors.size else 0,
        "floor": args.floor,
        "top_k": args.top_k,
        "corpus_words": targets,
        "corpus_fingerprint": words_fingerprint(targets),
        "n_corpus_words": len(targets),
        "n_corpus_words_in_source": len(reachable),
        "corpus_words_not_in_source": sorted(set(targets) - set(reachable)),
        "n_entries": len(table),
    }
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    dump_table(table, meta, out)
    print(
        f"{len(words)} source words, {len(targets)} corpus words "
        f"({len(reachable)} in source), {len(table)} entries -> {out} "
        f"({out.stat().st_size} bytes)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
