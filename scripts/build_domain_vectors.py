"""Train the ops-domain PPMI-SVD word vectors from the raw Stack Exchange pages.

    python scripts/build_domain_vectors.py --raw-dir /tmp/se_qa_raw

The raw pages are the snapshot ``scripts/fetch_stackexchange_qa.py`` fetched
on 2026-10-08 for the QA translation table; they are not committed. The
script refuses to build from any other snapshot (the SHA-256 over the pages
must equal ``meta.raw_sha256`` of ``data/qa/se_qa_translation.json.gz``), so
both outside models are trained on exactly the same data.
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ops_copilot.domain_vectors import DEFAULT_TABLE, docs_from_page, dump_table, train_docs, train_vectors  # noqa: E402
from ops_copilot.qa_translation import load_table as load_qa_table  # noqa: E402

LICENSE = (
    "CC BY-SA 4.0 (derived word statistics; input posts CC BY-SA 2.5 / 3.0 / 4.0 by post date)"
)
LICENSE_URL = "https://creativecommons.org/licenses/by-sa/4.0/"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--raw-dir", type=Path, required=True)
    ap.add_argument("--out", type=Path, default=DEFAULT_TABLE)
    args = ap.parse_args()
    files = sorted(args.raw_dir.glob("*.json.gz"))
    if not files:
        raise SystemExit(f"no raw pages in {args.raw_dir}")
    qa_meta = load_qa_table()["meta"]
    digest = hashlib.sha256()
    docs: list[dict] = []
    for f in files:
        raw = gzip.decompress(f.read_bytes())
        digest.update(f.name.encode() + b"\0" + hashlib.sha256(raw).digest())
        docs.extend(docs_from_page(f.name.split("-")[0], json.loads(raw)))
    if digest.hexdigest() != qa_meta["raw_sha256"]:
        raise SystemExit("raw pages differ from the snapshot the QA table was built from")
    seqs = train_docs(docs)
    meta = {
        "source": qa_meta["source"],
        "source_url": qa_meta["source_url"],
        "attribution": qa_meta["attribution"],
        "sites": qa_meta["sites"],
        "license": LICENSE,
        "license_url": LICENSE_URL,
        "fetched": qa_meta["fetched"],
        "raw_pages": len(files),
        "raw_sha256": digest.hexdigest(),
        "split": "train questions only (qa_translation.is_test false)",
    }
    dv = train_vectors(seqs, meta)
    sha = dump_table(dv, args.out)
    print(f"{len(dv.words)} words x {dv.vectors.shape[1]} dims from {dv.meta['n_tokens']:,} tokens "
          f"-> {args.out} ({args.out.stat().st_size:,} bytes, payload sha256 {sha[:12]})")


if __name__ == "__main__":
    main()
