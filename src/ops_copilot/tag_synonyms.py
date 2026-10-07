"""Stack Exchange tag synonyms: an external, ops-domain synonym resource.

The word-vector backoff (``word_vectors.py``) showed that a general-English
resource does not carry ops senses: ``latency`` and ``credential`` are not in
its vocabulary, and nothing in it says that *bounce* is a restart. The README
named the next honest step as an ops-domain resource that is also external.

Stack Exchange tag synonyms are that. On each site a synonym (``from_tag`` ->
``to_tag``) is proposed by a user and needs approval from users who hold
answer score in the target tag, so every pair was judged by practitioners of
that site's domain, years before this repo existed. ``SITES`` are the sites
whose subject is running systems (Server Fault, Super User, Unix & Linux,
Ask Ubuntu, DevOps, Database Administrators, Network Engineering, Information
Security) plus Stack Overflow. ``scripts/fetch_tag_synonyms.py`` snapshots
*every* synonym of those sites into ``data/tagsyn/`` with no eval-driven or
corpus-driven filtering; tests and CI only read the snapshot (offline).

Content is CC BY-SA 4.0 (Stack Exchange Inc. and each site's contributors).
"""

from __future__ import annotations

import gzip
import hashlib
import io
import json
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parents[2] / "data" / "tagsyn"
DEFAULT_SNAPSHOT = DATA_DIR / "stackexchange_tag_synonyms.json.gz"
API_URL = "https://api.stackexchange.com/2.3/tags/synonyms"
OPS_SITES: tuple[str, ...] = (
    "serverfault",
    "superuser",
    "unix",
    "askubuntu",
    "devops",
    "dba",
    "networkengineering",
    "security",
)
SITES: tuple[str, ...] = (*OPS_SITES, "stackoverflow")
# SHA-256 of the uncompressed snapshot payload fetched on 2026-10-07 (4,560
# synonyms; Stack Overflow cut to its 2,500 most-applied by the anonymous
# 25-page API limit). Applied counts drift daily, so a re-fetch will differ.
SNAPSHOT_SHA256 = "e1cff66cc42f02967d9121b6335ce0bd1e17b8230e12dd27d2b9c2417a230c44"
SNAPSHOT_N_PAIRS = 4560


def _payload(pairs: list[dict], meta: dict) -> bytes:
    rows = sorted(
        ({k: p[k] for k in ("site", "from_tag", "to_tag", "applied_count")} for p in pairs),
        key=lambda p: (p["site"], p["from_tag"], p["to_tag"]),
    )
    meta = dict(meta) | {
        "n_pairs": len(rows),
        "per_site": {s: sum(1 for r in rows if r["site"] == s) for s in meta.get("sites", [])},
    }
    return json.dumps(
        {"meta": meta, "pairs": rows}, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")


def dump_snapshot(pairs: list[dict], meta: dict, path: str | Path) -> str:
    """Write a byte-stable gzip snapshot (zero mtime); returns its payload SHA-256."""
    payload = _payload(pairs, meta)
    buf = io.BytesIO()
    with gzip.GzipFile(fileobj=buf, mode="wb", mtime=0, compresslevel=9) as gz:
        gz.write(payload)
    Path(path).write_bytes(buf.getvalue())
    return hashlib.sha256(payload).hexdigest()


def load_snapshot(path: str | Path | None = None) -> dict:
    """``{"meta": ..., "pairs": [{site, from_tag, to_tag, applied_count}, ...]}``."""
    with gzip.open(Path(path) if path else DEFAULT_SNAPSHOT, "rb") as fh:
        raw = fh.read()
    data = json.loads(raw)
    data["sha256"] = hashlib.sha256(raw).hexdigest()
    return data
