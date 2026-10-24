"""Fifth calibration set (``dev5``, 44 rows), split by golden source row.

Why it exists: the dev4 ``confirm`` half was scored once (2026-10-22) by the
unknown-words-only Datamuse arm, so it cannot confirm the next hypothesis in
that family (a word-meaning check on Datamuse candidates).
``data/eval/synonym_dev5.jsonl`` was written by hand on 2026-10-24, before the
Datamuse, WordNet or counter-fitted tables were queried for any of its words
and before any config was run on it.

Contents:

- 35 one-swap paraphrases of golden queries (25 ANSWER, 6 REFUSE_STALE,
  4 REFUSE_UNGROUNDED), golden label kept. Swaps are ops-style or everyday
  rewording (``latency -> turnaround``, ``on-call -> responder``,
  ``utilization -> occupancy``, ``freeze -> moratorium``, ``lag -> backlog``);
- 6 new absent-topic traps. Four put one unknown word next to corpus words,
  and three of those are **word-sense traps**: the unknown word is a plausible
  dictionary relative of a corpus word in a *different* sense (``colour`` of a
  feature ``flag``, a theatre ``audition`` next to ``production``, a
  ``vacation`` next to ``remaining ... budget``), the shape of PR #27's
  ``legal -> duty`` fail-open;
- 3 canary / PII / write paraphrases.

Every refusal row is **must-refuse** (``must_refuse_rows``).

Split and guards are dev4's: whole golden-source groups move together (traps
by their own id), salted-hash order per label, and ``vocabulary_problems``
rejects held-out words in any query, swap words shared with dev / held-out /
perturbation / fresh / dev2 / dev3 / **dev4**, and swap words repeated inside
dev5.
"""

from __future__ import annotations

import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path

from ops_copilot.synonym_dev2 import swapped_in
from ops_copilot.synonym_dev4 import OPENING, load_dev4
from ops_copilot.synonym_dev4 import vocabulary_problems as _dev4_problems

DEV5_PATH = Path(__file__).resolve().parents[2] / "data" / "eval" / "synonym_dev5.jsonl"
SPLIT_SALT = "dev5-tune-confirm-2026-10-24"
HALVES = ("tune", "confirm")


def load_dev5(path: str | Path | None = None) -> list[dict]:
    src = Path(path) if path else DEV5_PATH
    return [json.loads(ln) for ln in src.read_text(encoding="utf-8").splitlines() if ln.strip()]


def group_key(row: dict) -> str:
    return f"src{row['source_index']}" if "source_index" in row else row["id"]


def _hash(key: str) -> str:
    return hashlib.sha256(f"{SPLIT_SALT}:{key}".encode()).hexdigest()


def split_dev5(rows: list[dict] | None = None) -> dict[str, str]:
    """Row id -> ``tune`` / ``confirm``; whole source groups move together."""
    rows = load_dev5() if rows is None else rows
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
    rows = load_dev5() if rows is None else rows
    sp = split_dev5(rows)
    return [r for r in rows if sp[r["id"]] == name]


def must_refuse_rows(rows: list[dict]) -> list[dict]:
    """Rows whose expected decision is a refusal: they may never open."""
    return [r for r in rows if r["expect_decision"] not in OPENING]


def vocabulary_problems(rows: list[dict] | None = None) -> dict[str, list[str]]:
    """Row id -> problems (must be empty): dev4's guard plus dev4 swap words."""
    rows = load_dev5() if rows is None else rows
    out = {k: [p for p in v if not p.startswith("repeated_swap:")] for k, v in _dev4_problems(rows).items()}
    out = {k: v for k, v in out.items() if v}
    dev4_words: set[str] = set()
    for r in load_dev4():
        dev4_words |= swapped_in(r)
    seen = Counter(w for r in rows for w in swapped_in(r))
    for r in rows:
        probs = [f"shared_dev4:{t}" for t in sorted(swapped_in(r) & dev4_words)]
        probs += [f"repeated_swap:{t}" for t in sorted(w for w in swapped_in(r) if seen[w] > 1)]
        if probs:
            out.setdefault(r["id"], []).extend(probs)
    return out


def summary(rows: list[dict] | None = None) -> dict:
    rows = load_dev5() if rows is None else rows
    sp = split_dev5(rows)
    return {
        h: dict(sorted(Counter(r["expect_decision"] for r in rows if sp[r["id"]] == h).items()))
        for h in HALVES
    }
