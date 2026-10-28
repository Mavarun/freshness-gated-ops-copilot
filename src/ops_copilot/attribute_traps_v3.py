"""A third, unseen attribute-trap set for the credited-word check (written 2026-10-28).

Both earlier sets are spent: ``attribute_traps.jsonl`` (tune, confirm, then
calibration) and ``attribute_traps_v2.jsonl`` (tune in the 2026-10-27
seed-free calibration, confirm once, failed on at2-01). The credited-word
check (``passage_support.credited_word_problems``) was motivated by credits
seen on those spent rows (``taste <- one``), so its confirm needs traps no
config has seen. ``attribute_traps_v3.jsonl`` (38 rows) was written by hand on
2026-10-28, before any config was run on it:

- 18 attributes new to all sets (10 nouns such as ``nationality``,
  ``dialect``, ``vintage``, ``calories``, each in three forms; 8 adjectives such
  as ``How grumpy ...``), none in the corpus, none ``colour``;
- subjects taken round-robin from 12 golden pages (latency, the Redis pool, the
  error budget, the status page, the change window, the freeze, the runbook,
  on-call, the replica snapshot, the vault-transit window, blue-green, the
  inc-4821 webhook), a different spread from v1 and v2.

Every row is must-refuse. Split as v1 / v2 (whole attributes move together,
salted hash): the credited-word protocol (``credit_check.py``) uses ``tune`` in
calibration and ``confirm`` once.
"""

from __future__ import annotations

import hashlib
from collections import defaultdict
from pathlib import Path

from ops_copilot.attribute_traps import FORMS, load_traps, score_traps

TRAPS_V3_PATH = Path(__file__).resolve().parents[2] / "data" / "eval" / "attribute_traps_v3.jsonl"
SPLIT_SALT = "attribute-traps-v3-2026-10-28"
HALVES = ("tune", "confirm")


def load_traps_v3() -> list[dict]:
    return load_traps(TRAPS_V3_PATH)


def _hash(key: str) -> str:
    return hashlib.sha256(f"{SPLIT_SALT}:{key}".encode()).hexdigest()


def split_traps_v3(rows: list[dict] | None = None) -> dict[str, str]:
    """Row id -> half; nouns and adjectives are balanced separately, attributes stay whole."""
    rows = load_traps_v3() if rows is None else rows
    groups: dict[str, list[dict]] = defaultdict(list)
    for r in rows:
        groups[r["attribute"]].append(r)
    out: dict[str, str] = {}
    for kind in ("noun", "adjective"):
        filled = {h: 0 for h in HALVES}
        keys = [a for a in groups if (groups[a][0]["form"] == "how_adj_is") == (kind == "adjective")]
        for attr in sorted(keys, key=_hash):
            side = min(HALVES, key=lambda h: (filled[h], HALVES.index(h)))
            filled[side] += len(groups[attr])
            for m in groups[attr]:
                out[m["id"]] = side
    return out


def half_v3(name: str, rows: list[dict] | None = None) -> list[dict]:
    if name not in HALVES:
        raise ValueError(f"unknown half {name!r}")
    rows = load_traps_v3() if rows is None else rows
    sp = split_traps_v3(rows)
    return [r for r in rows if sp[r["id"]] == name]


__all__ = ["FORMS", "load_traps_v3", "split_traps_v3", "half_v3", "score_traps", "TRAPS_V3_PATH"]
