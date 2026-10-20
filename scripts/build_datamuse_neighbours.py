#!/usr/bin/env python3
"""Build data/datamuse/ml_neighbours.json.gz from fetched Datamuse ``ml`` lists.

Run locally once (CI only reads the committed table):

    python scripts/fetch_datamuse_ml.py --raw-dir /tmp/datamuse_raw
    python scripts/build_datamuse_neighbours.py --raw-dir /tmp/datamuse_raw

Every corpus word must have a raw response (the queries are exactly the corpus
words; no eval file is read). The SHA-256 of the canonical raw responses and
the fetch date are pinned in ``meta`` because the live API can change; the raw
lists themselves are not committed.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ops_copilot.corpus import Corpus  # noqa: E402
from ops_copilot.datamuse_senses import (  # noqa: E402
    DEFAULT_TABLE,
    MAX_RESULTS,
    ROW_FORMAT,
    SOURCE_ATTRIBUTION,
    SOURCE_DOCS,
    SOURCE_NAME,
    SOURCE_URL,
    build_neighbour_table,
    dump_table,
)
from ops_copilot.word_vectors import corpus_words, words_fingerprint  # noqa: E402


def raw_digest(responses: dict[str, list]) -> str:
    canon = json.dumps(responses, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(canon.encode("utf-8")).hexdigest()


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--raw-dir", required=True)
    ap.add_argument("--out", default=str(DEFAULT_TABLE))
    ap.add_argument("--fetched-on", default=None, help="YYYY-MM-DD (default: newest raw file mtime)")
    args = ap.parse_args(argv)
    raw = Path(args.raw_dir)
    targets = corpus_words(f"{c.title} {c.text}" for c in Corpus().chunks)
    missing = [w for w in targets if not (raw / f"{w}.json").exists()]
    if missing:
        raise SystemExit(f"{len(missing)} corpus words have no raw response, e.g. {missing[:5]}")
    responses = {w: json.loads((raw / f"{w}.json").read_text(encoding="utf-8")) for w in targets}
    fetched_on = args.fetched_on or dt.date.fromtimestamp(
        max((raw / f"{w}.json").stat().st_mtime for w in targets)
    ).isoformat()
    table = build_neighbour_table(responses, targets)
    meta = {
        "source": SOURCE_NAME,
        "source_url": SOURCE_URL,
        "source_docs": SOURCE_DOCS,
        "attribution": SOURCE_ATTRIBUTION,
        "max_results": MAX_RESULTS,
        "fetched_on": fetched_on,
        "raw_sha256": raw_digest(responses),
        "queried_words": targets,
        "corpus_words": targets,
        "corpus_fingerprint": words_fingerprint(targets),
        "n_corpus_words": len(targets),
        "n_corpus_words_with_results": sum(bool(responses[w]) for w in targets),
        "n_raw_results": sum(len(v) for v in responses.values()),
        "row_format": list(ROW_FORMAT),
        "n_entries": len(table),
    }
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    dump_table(table, meta, out)
    print(
        f"{len(targets)} corpus words queried ({meta['n_corpus_words_with_results']} with results), "
        f"{meta['n_raw_results']} raw results, {len(table)} entries -> {out} ({out.stat().st_size} bytes)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
