#!/usr/bin/env python3
"""Build data/wordnet/wn_lemmas.txt.gz from Princeton WordNet 3.0 (run once; CI reads the file).

    python scripts/build_dictionary_words.py --source /tmp/wordnet.zip

Same archive and SHA-256 check as ``build_wordnet_neighbours.py``. Prints the sha256
of the uncompressed table to pin in ``ops_copilot.dictionary.TABLE_SHA256``.
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import io
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ops_copilot.dictionary import EXC_FILES, INDEX_FILES, TABLE, parse_lemmas  # noqa: E402
from ops_copilot.wordnet_senses import SOURCE_SHA256  # noqa: E402


def _lines(zf: zipfile.ZipFile, name: str) -> list[str]:
    member = next(n for n in zf.namelist() if n.endswith("/" + name))
    with zf.open(member) as fh:
        return list(io.TextIOWrapper(fh, encoding="utf-8"))


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--source", required=True)
    ap.add_argument("--out", default=str(TABLE))
    args = ap.parse_args(argv)
    src = Path(args.source)
    if hashlib.sha256(src.read_bytes()).hexdigest() != SOURCE_SHA256:
        raise SystemExit("unexpected wordnet.zip sha256")
    with zipfile.ZipFile(src) as zf:
        idx = [ln for f in INDEX_FILES for ln in _lines(zf, f)]
        exc = [ln for f in EXC_FILES for ln in _lines(zf, f)]
    words = sorted(parse_lemmas(idx, exc))
    raw = ("\n".join(words) + "\n").encode("ascii")
    Path(args.out).write_bytes(gzip.compress(raw, mtime=0))
    print(f"{len(words)} lemmas -> {args.out}; sha256 {hashlib.sha256(raw).hexdigest()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
