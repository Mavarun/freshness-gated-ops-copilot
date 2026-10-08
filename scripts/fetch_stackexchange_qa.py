#!/usr/bin/env python3
"""Fetch question-title / answer pairs from the ops Stack Exchange sites, once.

Run locally once (CI and tests only read the committed tokenised snapshot):

    python scripts/fetch_stackexchange_qa.py --raw-dir /tmp/se_qa_raw
    python scripts/build_qa_translation.py --raw-dir /tmp/se_qa_raw

This is the *outside* training data for the answer-support model
(``ops_copilot.qa_translation``): what people on Server Fault, Super User,
Unix & Linux, Ask Ubuntu, DBA, DevOps, Network Engineering and Information
Security wrote when *answering* a question. Nothing here is filtered by this
repo's eval or corpus words; the pages are simply the most-voted and the most
recently active questions of each site (the anonymous API serves at most 25
pages of 100 per query).

Uses the public, unauthenticated Stack Exchange API v2.3 (300 requests a day
per IP; this needs ``2 * sum(PAGES.values())`` = 300 requests, so a re-run
may need two days; finished pages are skipped). The filter
id below asks for question titles plus every answer's markdown body. Responses
are gzip-compressed and the client honours ``backoff``. Raw pages are cached in
``--raw-dir`` (outside the repo; about 1.4 MB a page). Content is licensed
CC BY-SA (2.5 / 3.0 / 4.0 by post date, recorded per answer); attribution and
the per-licence counts go into the snapshot's ``meta``, and
``data/qa/NOTICE.md`` carries the licence note for the committed table.
"""

from __future__ import annotations

import argparse
import gzip
import json
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

API_URL = "https://api.stackexchange.com/2.3/questions"
# include=question.answers;answer.body_markdown, exclude owners and tags.
FILTER = "!)rfa1JJqkEBqSn599Kgz"
PAGES = {
    "serverfault": 25,
    "superuser": 25,
    "unix": 25,
    "askubuntu": 20,
    "dba": 15,
    "security": 15,
    "devops": 13,
    "networkengineering": 12,
}
# Each site is read twice: most-voted questions, then most recently active
# ones (a different, mostly disjoint slice; duplicates are dropped at build
# time by (site, question id)).
SORTS: tuple[str, ...] = ("votes", "activity")


def fetch_page(site: str, page: int, sort: str = "votes") -> dict:
    query = urllib.parse.urlencode(
        {
            "site": site,
            "pagesize": 100,
            "page": page,
            "order": "desc",
            "sort": sort,
            "filter": FILTER,
        }
    )
    req = urllib.request.Request(
        f"{API_URL}?{query}", headers={"Accept-Encoding": "gzip", "User-Agent": "ops-copilot"}
    )
    for attempt in range(6):
        try:
            with urllib.request.urlopen(req, timeout=120) as resp:
                raw = resp.read()
            break
        except urllib.error.HTTPError as err:  # throttle_violation comes back as 400
            raw = err.read()
            msg = json.loads(gzip.decompress(raw) if raw[:2] == b"\x1f\x8b" else raw)
            print(f"{site} p{page}: HTTP {err.code} {msg.get('error_name')}: {msg.get('error_message')}", flush=True)
            if attempt == 5:
                raise
            time.sleep(30 * (attempt + 1))
    body = json.loads(gzip.decompress(raw) if raw[:2] == b"\x1f\x8b" else raw)
    if "error_id" in body:
        raise SystemExit(f"{site} p{page}: API error {body['error_id']} {body.get('error_message')}")
    return body


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--raw-dir", type=Path, required=True)
    ap.add_argument("--pause", type=float, default=0.3)
    ap.add_argument("--sites", nargs="*", default=list(PAGES), help="subset (one process per site is fine)")
    args = ap.parse_args()
    args.raw_dir.mkdir(parents=True, exist_ok=True)
    for site in args.sites:
        for sort in SORTS:
            for page in range(1, PAGES[site] + 1):
                path = args.raw_dir / f"{site}-{sort}-p{page:02d}.json.gz"
                if path.exists():
                    continue
                body = fetch_page(site, page, sort)
                path.write_bytes(gzip.compress(json.dumps(body).encode(), mtime=0))
                print(f"{site} {sort} p{page}: {len(body.get('items', []))} questions, quota {body.get('quota_remaining')}", flush=True)
                if not body.get("has_more"):
                    break
                time.sleep(max(args.pause, float(body.get("backoff", 0))))


if __name__ == "__main__":
    main()
