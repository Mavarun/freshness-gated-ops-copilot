#!/usr/bin/env python3
"""Snapshot every Stack Exchange tag synonym of the ops / sysadmin sites.

Run locally once (CI and tests only read the committed snapshot):

    python scripts/fetch_tag_synonyms.py

Tag synonyms are proposed and voted on by each site's community (a synonym
needs users with tag score in the target tag to approve it), so they are an
ops-domain synonym resource written by people who never saw this repo's eval.
*Every* synonym of every site in ``SITES`` is kept: no filtering by eval or
corpus words happens here (``tag_synonyms.build_substitute_table`` restricts
targets to corpus words later, from this file alone).

Uses the public, unauthenticated Stack Exchange API v2.3 (300 requests a day
per IP; this needs about 50). Anonymous clients may read at most 25 pages of
100, so pages are requested most-applied first: every ops site fits whole,
and Stack Overflow (5,332 synonyms on 2026-10-07) keeps its 2,500 most-applied
synonyms. The snapshot's ``meta.truncated`` records which sites were cut. The API always gzip-compresses responses and
asks clients to honour ``backoff``. Content is CC BY-SA 4.0 (attribution in
the snapshot's ``meta``).
"""

from __future__ import annotations

import argparse
import gzip
import json
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ops_copilot.tag_synonyms import (  # noqa: E402
    API_URL,
    DEFAULT_SNAPSHOT,
    SITES,
    dump_snapshot,
)


MAX_PAGES = 25  # anonymous API limit


def fetch_site(site: str, *, pause: float = 0.25) -> tuple[list[dict], bool]:
    """All synonyms of ``site`` (most-applied first); ``True`` if cut at MAX_PAGES."""
    out: list[dict] = []
    page = 1
    while True:
        query = urllib.parse.urlencode(
            {"site": site, "pagesize": 100, "page": page, "order": "desc", "sort": "applied"}
        )
        req = urllib.request.Request(
            f"{API_URL}?{query}", headers={"Accept-Encoding": "gzip", "User-Agent": "ops-copilot"}
        )
        with urllib.request.urlopen(req, timeout=60) as resp:
            raw = resp.read()
        body = json.loads(gzip.decompress(raw) if raw[:2] == b"\x1f\x8b" else raw)
        if "error_id" in body:
            raise SystemExit(f"{site}: API error {body['error_id']} {body.get('error_message')}")
        for item in body.get("items", []):
            out.append(
                {
                    "site": site,
                    "from_tag": item["from_tag"],
                    "to_tag": item["to_tag"],
                    "applied_count": int(item.get("applied_count", 0)),
                }
            )
        if not body.get("has_more"):
            return out, False
        if page >= MAX_PAGES:
            return out, True
        page += 1
        time.sleep(max(pause, float(body.get("backoff", 0))))


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", default=str(DEFAULT_SNAPSHOT))
    ap.add_argument("--sites", nargs="*", default=list(SITES))
    args = ap.parse_args(argv)
    pairs: list[dict] = []
    truncated: list[str] = []
    for site in args.sites:
        got, cut = fetch_site(site)
        print(f"{site}: {len(got)} synonyms{' (truncated)' if cut else ''}", flush=True)
        pairs.extend(got)
        if cut:
            truncated.append(site)
    meta = {
        "source": "Stack Exchange tag synonyms (API v2.3 /tags/synonyms)",
        "source_url": API_URL,
        "license": "CC BY-SA 4.0, Stack Exchange Inc. and the contributors of each site",
        "fetched": time.strftime("%Y-%m-%d"),
        "sites": list(args.sites),
        "order": "applied_count desc",
        "max_pages": MAX_PAGES,
        "truncated": truncated,
    }
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    digest = dump_snapshot(pairs, meta, out)
    print(f"{len(pairs)} synonyms -> {out} ({out.stat().st_size} bytes, sha256 {digest})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
