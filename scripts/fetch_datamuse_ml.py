#!/usr/bin/env python3
"""Fetch Datamuse ``ml`` (means-like) lists for every corpus word (raw, not committed).

    python scripts/fetch_datamuse_ml.py --raw-dir /tmp/datamuse_raw

Queries are the corpus content words only (``word_vectors.corpus_words`` over
``data/corpus``); no eval file is read. One JSON file per word is written to
``--raw-dir``; existing files are kept (resumable). CI never runs this.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.parse
from concurrent.futures import ThreadPoolExecutor
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ops_copilot.corpus import Corpus  # noqa: E402
from ops_copilot.datamuse_senses import MAX_RESULTS, SOURCE_URL  # noqa: E402
from ops_copilot.word_vectors import corpus_words  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--raw-dir", required=True)
    ap.add_argument("--delay", type=float, default=0.25, help="seconds between a worker's requests")
    ap.add_argument("--retries", type=int, default=4)
    ap.add_argument("--workers", type=int, default=4, help="concurrent requests (keep small)")
    args = ap.parse_args(argv)
    raw = Path(args.raw_dir)
    raw.mkdir(parents=True, exist_ok=True)
    words = corpus_words(f"{c.title} {c.text}" for c in Corpus().chunks)
    todo = [w for w in words if not (raw / f"{w}.json").exists()]

    def fetch(w: str) -> None:
        url = SOURCE_URL.format(word=urllib.parse.quote(w), max=MAX_RESULTS)
        req = urllib.request.Request(url, headers={"User-Agent": "freshness-gated-ops-copilot/0.1"})
        for attempt in range(args.retries + 1):
            try:
                with urllib.request.urlopen(req, timeout=60) as resp:
                    items = json.load(resp)
                break
            except OSError:  # URLError, TLS EOF, timeouts: back off and retry
                if attempt == args.retries:
                    raise
                time.sleep(2.0 * (attempt + 1))
        (raw / f"{w}.json").write_text(json.dumps(items, sort_keys=True), encoding="utf-8")
        time.sleep(args.delay)

    with ThreadPoolExecutor(max_workers=max(1, args.workers)) as pool:
        list(pool.map(fetch, todo))
    fetched = len(todo)
    print(f"{len(words)} corpus words, {fetched} fetched -> {raw}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
