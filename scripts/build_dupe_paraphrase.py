#!/usr/bin/env python3
"""Build data/dupes/se_duplicate_paraphrase.json.gz from the Stack Exchange data dumps, once.

    # the 2024-04 dumps of the eight ops sites (about 4.5 GB, outside the repo):
    #   https://archive.org/download/stackexchange/<site>.7z
    python scripts/build_dupe_paraphrase.py --dump-dir /tmp/se_dumps

Reads only ``PostLinks.xml`` (``LinkTypeId=3`` = closed as duplicate: PostId is the
duplicate, RelatedPostId the original) and the question titles of ``Posts.xml``, streamed
out of each archive with ``7z x -so`` (needs the ``7z`` binary). Every duplicate link of
every site is used; nothing is filtered by this repo's eval or corpus words. The committed
table holds word statistics only (``dupe_paraphrase.build_table``), no titles or post ids;
the archives are pinned by SHA-256 in ``meta``. CI and tests only read the table.
"""

from __future__ import annotations

import argparse
import hashlib
import subprocess
import sys
import xml.etree.ElementTree as ET
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ops_copilot.dupe_paraphrase import DEFAULT_TABLE, build_table, dump_table  # noqa: E402

SITES = {
    "serverfault": "serverfault.com",
    "superuser": "superuser.com",
    "unix": "unix.stackexchange.com",
    "askubuntu": "askubuntu.com",
    "dba": "dba.stackexchange.com",
    "security": "security.stackexchange.com",
    "devops": "devops.stackexchange.com",
    "networkengineering": "networkengineering.stackexchange.com",
}
DUPLICATE_LINK = "3"


def _rows(archive: Path, member: str):
    proc = subprocess.Popen(["7z", "x", "-so", str(archive), member], stdout=subprocess.PIPE,
                            stderr=subprocess.DEVNULL)
    for _, el in ET.iterparse(proc.stdout, events=("end",)):
        if el.tag == "row":
            yield el.attrib
        el.clear()
    proc.wait()


def site_pairs(archive: Path) -> list[tuple[str, str]]:
    links = [(int(r["PostId"]), int(r["RelatedPostId"])) for r in _rows(archive, "PostLinks.xml")
             if r.get("LinkTypeId") == DUPLICATE_LINK]
    need = {i for pair in links for i in pair}
    titles = {}
    for r in _rows(archive, "Posts.xml"):
        if r.get("PostTypeId") == "1" and int(r["Id"]) in need and r.get("Title"):
            titles[int(r["Id"])] = r["Title"]
    return [(titles[a], titles[b]) for a, b in sorted(set(links)) if a in titles and b in titles and a != b]


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dump-dir", type=Path, required=True)
    ap.add_argument("--out", type=Path, default=DEFAULT_TABLE)
    ap.add_argument("--jobs", type=int, default=4)
    args = ap.parse_args()
    pairs: list[tuple[str, str]] = []
    per_site, archives = Counter(), {}
    paths = {site: args.dump_dir / f"{stem}.7z" for site, stem in SITES.items()}
    with ProcessPoolExecutor(max_workers=args.jobs) as pool:  # one archive per process
        done = dict(zip(paths, pool.map(site_pairs, paths.values())))
    for site, stem in SITES.items():
        path = paths[site]
        got = done[site]
        per_site[site] = len(got)
        archives[f"{stem}.7z"] = sha256(path)
        pairs += got
        print(f"{site}: {len(got)} duplicate title pairs", flush=True)
    table = build_table(pairs)
    meta = {
        "source": "Stack Exchange data dump 2024-04 (archive.org/details/stackexchange), PostLinks LinkTypeId=3",
        "license": "CC BY-SA 4.0",
        "sites": dict(per_site),
        "archives_sha256": archives,
        "n_words": len(table["rows"]),
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    digest = dump_table(table, meta, args.out)
    print(f"{table['n_pairs']} pairs, {len(table['rows'])} words -> {args.out} (payload sha256 {digest})")


if __name__ == "__main__":
    main()
