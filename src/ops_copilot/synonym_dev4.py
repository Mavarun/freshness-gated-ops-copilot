"""Fourth calibration set (``dev4``, 44 rows), split by golden source row.

Why it exists: the dev3 ``confirm`` half was scored once by the dev3-chosen
context-gated Datamuse arm and once post-hoc by the unknown-words-only
variant (2026-10-21), so it can no longer confirm that variant.
``data/eval/synonym_dev4.jsonl`` was written by hand on 2026-10-22, before
the Datamuse or WordNet tables were queried for any of its words and before
any config was run on it.

Contents:

- 35 one-swap paraphrases of golden queries (25 ANSWER, 6 REFUSE_STALE,
  4 REFUSE_UNGROUNDED), golden label kept. Swaps are ops-style or everyday
  rewording (``restart -> bounce``, ``on-call -> firefighter``,
  ``utilization -> usage``, ``freeze -> lockdown``, ``rollback -> undo``);
- 6 new absent-topic traps, four with one unknown word next to corpus words
  (``What is the checkout loyalty latency?``), the shape that an unknown-word
  mapping is most likely to open;
- 3 canary / PII / write paraphrases.

Every refusal row is **must-refuse**: ``must_refuse_rows`` lists them, and the
dev4 protocol (``datamuse_dev4.py``) treats any of them turning into ANSWER /
PROPOSE_WRITE as disqualifying, on top of the no-new-error rule.

Split and guards are dev3's (``synonym_dev3``): whole golden-source groups move
together (traps by their own id), salted-hash order per label, and
``vocabulary_problems`` rejects held-out words in any query, swap words shared
with dev / held-out / perturbation / fresh / dev2 / **dev3**, and swap words
repeated inside dev4.
"""

from __future__ import annotations

import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path

from ops_copilot.synonym_dev2 import swapped_in
from ops_copilot.synonym_dev3 import load_dev3
from ops_copilot.synonym_dev3 import vocabulary_problems as _dev3_problems

DEV4_PATH = Path(__file__).resolve().parents[2] / "data" / "eval" / "synonym_dev4.jsonl"
SPLIT_SALT = "dev4-tune-confirm-2026-10-22"
HALVES = ("tune", "confirm")
OPENING = frozenset({"ANSWER", "PROPOSE_WRITE"})


def load_dev4(path: str | Path | None = None) -> list[dict]:
    src = Path(path) if path else DEV4_PATH
    return [json.loads(ln) for ln in src.read_text(encoding="utf-8").splitlines() if ln.strip()]


def group_key(row: dict) -> str:
    return f"src{row['source_index']}" if "source_index" in row else row["id"]


def _hash(key: str) -> str:
    return hashlib.sha256(f"{SPLIT_SALT}:{key}".encode()).hexdigest()


def split_dev4(rows: list[dict] | None = None) -> dict[str, str]:
    """Row id -> ``tune`` / ``confirm``; whole source groups move together."""
    rows = load_dev4() if rows is None else rows
    groups: dict[str, list[dict]] = defaultdict(list)
    for r in rows:
        groups[group_key(r)].append(r)
    by_label: dict[str, list[str]] = defaultdict(list)
    for key, members in groups.items():
        labels = {m["expect_decision"] for m in members}
        if len(labels) != 1:
            raise ValueError(f"group {key} mixes labels {sorted(labels)}")
        by_label[labels.pop()].append(key)
    out: dict[str, str] = {}
    for label in sorted(by_label):
        filled = {h: 0 for h in HALVES}
        for key in sorted(by_label[label], key=_hash):
            side = min(HALVES, key=lambda h: (filled[h], HALVES.index(h)))
            filled[side] += len(groups[key])
            for m in groups[key]:
                out[m["id"]] = side
    return out


def half(name: str, rows: list[dict] | None = None) -> list[dict]:
    if name not in HALVES:
        raise ValueError(f"unknown half {name!r}")
    rows = load_dev4() if rows is None else rows
    sp = split_dev4(rows)
    return [r for r in rows if sp[r["id"]] == name]


def must_refuse_rows(rows: list[dict]) -> list[dict]:
    """Rows whose expected decision is a refusal: they may never open."""
    return [r for r in rows if r["expect_decision"] not in OPENING]


def vocabulary_problems(rows: list[dict] | None = None) -> dict[str, list[str]]:
    """Row id -> problems (must be empty): dev3's guard plus dev3 swap words."""
    rows = load_dev4() if rows is None else rows
    out = {k: [p for p in v if not p.startswith("repeated_swap:")] for k, v in _dev3_problems(rows).items()}
    out = {k: v for k, v in out.items() if v}
    dev3_words: set[str] = set()
    for r in load_dev3():
        dev3_words |= swapped_in(r)
    seen = Counter(w for r in rows for w in swapped_in(r))
    for r in rows:
        probs = [f"shared_dev3:{t}" for t in sorted(swapped_in(r) & dev3_words)]
        probs += [f"repeated_swap:{t}" for t in sorted(w for w in swapped_in(r) if seen[w] > 1)]
        if probs:
            out.setdefault(r["id"], []).extend(probs)
    return out


def summary(rows: list[dict] | None = None) -> dict:
    rows = load_dev4() if rows is None else rows
    sp = split_dev4(rows)
    return {
        h: dict(sorted(Counter(r["expect_decision"] for r in rows if sp[r["id"]] == h).items()))
        for h in HALVES
    }
