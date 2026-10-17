#!/usr/bin/env python3
"""Build data/wordnet/wn_noun_neighbours.json.gz from Princeton WordNet 3.0.

Run locally once (CI only reads the committed table):

    curl -L -o /tmp/wordnet.zip \\
      https://raw.githubusercontent.com/nltk/nltk_data/gh-pages/packages/corpora/wordnet.zip
    python scripts/build_wordnet_neighbours.py --source /tmp/wordnet.zip

The archive's SHA-256 is checked against ``SOURCE_SHA256`` unless
``--allow-other-source`` is given. Every single-word noun lemma is mapped onto
the corpus words its senses reach (synset, direct hyper/hyponym, co-hyponym);
no eval word list is read.
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
from ops_copilot.word_vectors import corpus_words, words_fingerprint  # noqa: E402
from ops_copilot.wordnet_senses import (  # noqa: E402
    DEFAULT_TABLE,
    SOURCE_LICENSE,
    SOURCE_NAME,
    SOURCE_SHA256,
    SOURCE_URL,
    build_neighbour_table,
    dump_table,
    parse_data_noun,
    parse_index_noun,
)


def _read(zf: zipfile.ZipFile, name: str):
    member = next(n for n in zf.namelist() if n.endswith("/" + name) or n == name)
    with zf.open(member) as fh:
        yield from io.TextIOWrapper(fh, encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--source", required=True, help="wordnet.zip (nltk_data)")
    ap.add_argument("--out", default=str(DEFAULT_TABLE))
    ap.add_argument("--allow-other-source", action="store_true")
    args = ap.parse_args(argv)

    src = Path(args.source)
    digest = hashlib.sha256(src.read_bytes()).hexdigest()
    if digest != SOURCE_SHA256 and not args.allow_other_source:
        raise SystemExit(f"unexpected source sha256 {digest} (want {SOURCE_SHA256})")
    with zipfile.ZipFile(src) as zf:
        synsets = parse_data_noun(_read(zf, "data.noun"))
        senses = parse_index_noun(_read(zf, "index.noun"))
    targets = corpus_words(f"{c.title} {c.text}" for c in Corpus().chunks)
    table = build_neighbour_table(synsets, senses, targets)
    in_source = sorted(t for t in targets if t in senses)
    meta = {
        "source": SOURCE_NAME,
        "source_url": SOURCE_URL,
        "source_sha256": digest,
        "source_license": SOURCE_LICENSE,
        "n_synsets": len(synsets),
        "n_lemmas": len(senses),
        "relations": ["syn", "hyper", "hypo", "sib"],
        "row_format": ["corpus_word", "relation", "path", "fan_out", "sense_rank"],
        "corpus_words": targets,
        "corpus_fingerprint": words_fingerprint(targets),
        "n_corpus_words": len(targets),
        "n_corpus_words_in_source": len(in_source),
        "corpus_words_not_in_source": sorted(set(targets) - set(in_source)),
        "n_entries": len(table),
    }
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    dump_table(table, meta, out)
    print(
        f"{len(synsets)} synsets, {len(senses)} lemmas, {len(targets)} corpus words "
        f"({len(in_source)} in WordNet), {len(table)} entries -> {out} ({out.stat().st_size} bytes)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
