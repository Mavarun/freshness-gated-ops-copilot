#!/usr/bin/env python3
"""Build data/wiktionary/computing_senses.json.gz from the Wiktextract dump.

Run locally once (CI and tests only read the committed extract):

    curl -L -o /tmp/kaikki_en.jsonl \\
      https://kaikki.org/dictionary/English/kaikki.org-dictionary-English.jsonl
    python scripts/build_wiktionary_senses.py --source /tmp/kaikki_en.jsonl

Keeps every English sense whose topic is in ``OPS_TOPICS``; nothing is
filtered by eval or corpus words. Records the dump's SHA-256 and size.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ops_copilot.wiktionary_senses import (  # noqa: E402
    DEFAULT_EXTRACT,
    OPS_TOPICS,
    SOURCE_NAME,
    SOURCE_URL,
    dump_extract,
    extract_senses,
)

_TOPIC_BYTES = tuple(f'"{t}"'.encode() for t in OPS_TOPICS)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--source", required=True)
    ap.add_argument("--out", default=str(DEFAULT_EXTRACT))
    args = ap.parse_args(argv)
    src = Path(args.source)
    digest = hashlib.sha256()
    senses: list[dict] = []
    n_entries = 0
    t0 = time.time()
    with src.open("rb") as fh:
        for line in fh:
            digest.update(line)
            n_entries += 1
            # cheap prefilter; extract_senses re-checks everything on the parsed entry
            if b'"en"' not in line or not any(t in line for t in _TOPIC_BYTES):
                continue
            senses.extend(extract_senses(json.loads(line)))
    meta = {
        "source": SOURCE_NAME,
        "source_url": SOURCE_URL,
        "source_sha256": digest.hexdigest(),
        "source_bytes": src.stat().st_size,
        "source_entries": n_entries,
        "license": "CC BY-SA 4.0 and GFDL (Wiktionary contributors); extraction by Wiktextract",
        "built": time.strftime("%Y-%m-%d"),
        "topics": list(OPS_TOPICS),
    }
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    payload_sha = dump_extract(senses, meta, out)
    print(
        f"{n_entries} entries, {len(senses)} domain senses -> {out} "
        f"({out.stat().st_size} bytes, payload sha256 {payload_sha}, {time.time() - t0:.0f}s)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
