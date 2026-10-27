"""A second, unseen attribute-trap set for the seed-free null test (written 2026-10-27).

Both halves of ``attribute_traps.jsonl`` are spent (tune for the 2026-10-25
design, confirm once, and all 36 are now in the calibration of the seed-free
test), so a confirm needs traps no config has seen. ``attribute_traps_v2.jsonl``
(40 rows) was written by hand on 2026-10-27, before any config was run on it,
with the same four question forms but:

- 18 new attributes (11 nouns such as ``taste``, ``zodiac``, ``wingspan``, each
  in three forms; 7 adjectives such as ``How juicy ...``), none of them used by
  the first set, ``colour``, or the corpus;
- other subjects (the LaunchDarkly flag, the Kafka lag runbook, the Vault AppRole
  schedule, the auth token TTL, the Grafana SLI snapshot, INC-3104, ...), so the
  set is not the first one's pages again.

Every row is must-refuse: any refusal is correct, ANSWER / PROPOSE_WRITE opens.
Split as the first set (whole attributes move together, salted hash) into
``tune`` / ``confirm``; the seed-free protocol (``passage_null_pool.py``) uses
the tune half in calibration and the confirm half once.
"""

from __future__ import annotations

import hashlib
from collections import defaultdict
from pathlib import Path

from ops_copilot.attribute_traps import FORMS, load_traps, score_traps

TRAPS_V2_PATH = Path(__file__).resolve().parents[2] / "data" / "eval" / "attribute_traps_v2.jsonl"
SPLIT_SALT = "attribute-traps-v2-2026-10-27"
HALVES = ("tune", "confirm")


def load_traps_v2() -> list[dict]:
    return load_traps(TRAPS_V2_PATH)


def _hash(key: str) -> str:
    return hashlib.sha256(f"{SPLIT_SALT}:{key}".encode()).hexdigest()


def split_traps_v2(rows: list[dict] | None = None) -> dict[str, str]:
    rows = load_traps_v2() if rows is None else rows
    groups: dict[str, list[dict]] = defaultdict(list)
    for r in rows:
        groups[r["attribute"]].append(r)
    filled = {h: 0 for h in HALVES}
    out: dict[str, str] = {}
    for attr in sorted(groups, key=_hash):
        side = min(HALVES, key=lambda h: (filled[h], HALVES.index(h)))
        filled[side] += len(groups[attr])
        for m in groups[attr]:
            out[m["id"]] = side
    return out


def half_v2(name: str, rows: list[dict] | None = None) -> list[dict]:
    if name not in HALVES:
        raise ValueError(f"unknown half {name!r}")
    rows = load_traps_v2() if rows is None else rows
    sp = split_traps_v2(rows)
    return [r for r in rows if sp[r["id"]] == name]


__all__ = ["FORMS", "load_traps_v2", "split_traps_v2", "half_v2", "score_traps", "TRAPS_V2_PATH"]
