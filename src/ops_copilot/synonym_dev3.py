"""Third calibration set (``dev3``, 45 rows), split by golden source row.

Why it exists: the dev2 ``confirm`` half has now been scored twice (WordNet on
2026-10-19, Datamuse on 2026-10-20), so it is no longer a clean confirm set
for read-path backoffs. ``data/eval/synonym_dev3.jsonl`` was written by hand
on 2026-10-21, before the Datamuse or WordNet tables were queried for any of
its words and before any config was run on it.

Contents:

- 35 one-swap paraphrases of golden queries (25 ANSWER, 6 REFUSE_STALE,
  4 REFUSE_UNGROUNDED), golden label kept. Most swaps are ops-style or
  everyday rewording (``latency -> slowness``, ``status -> uptime``,
  ``freeze -> blackout``, ``lag -> backlog``), noun and non-noun alike;
- 6 new absent-topic traps, most with a single unknown word next to corpus
  words (``What is the checkout coupon latency?``);
- 4 canary / PII / write paraphrases.

Two fixes recorded as dev2 weaknesses (PR #24) are built in:

- **split by golden source row**: every row with the same ``source_index``
  (traps: their own id) lands in the same half, so two paraphrases of one
  golden row can no longer both sit in ``calib`` and leave ``confirm`` without
  that topic, nor straddle the halves and leak a topic across them;
- groups are assigned in salted-hash order, per expected label, to whichever
  half currently has fewer rows of that label (ties -> ``calib``).

Guards (``vocabulary_problems``): no query contains a held-out word (folded),
and no swapped-in word is a dev / held-out word, a replacement word of the
perturbation map, or a swapped-in word of the fresh set or dev2. No swapped-in
word repeats inside dev3 either, so a word cannot sit in both halves.
"""

from __future__ import annotations

import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path

from ops_copilot.synonym_dev2 import load_dev2, swapped_in
from ops_copilot.synonym_dev2 import vocabulary_problems as _dev2_problems

DEV3_PATH = Path(__file__).resolve().parents[2] / "data" / "eval" / "synonym_dev3.jsonl"
SPLIT_SALT = "dev3-calib-confirm-2026-10-21"
HALVES = ("calib", "confirm")


def load_dev3(path: str | Path | None = None) -> list[dict]:
    src = Path(path) if path else DEV3_PATH
    return [json.loads(ln) for ln in src.read_text(encoding="utf-8").splitlines() if ln.strip()]


def group_key(row: dict) -> str:
    return f"src{row['source_index']}" if "source_index" in row else row["id"]


def _hash(key: str) -> str:
    return hashlib.sha256(f"{SPLIT_SALT}:{key}".encode()).hexdigest()


def split_dev3(rows: list[dict] | None = None) -> dict[str, str]:
    """Row id -> ``calib`` / ``confirm``; whole source groups move together."""
    rows = load_dev3() if rows is None else rows
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
    rows = load_dev3() if rows is None else rows
    sp = split_dev3(rows)
    return [r for r in rows if sp[r["id"]] == name]


def vocabulary_problems(rows: list[dict] | None = None) -> dict[str, list[str]]:
    """Row id -> problems (must be empty).

    dev2's guard (held-out words in the query; swap words shared with dev /
    held-out / perturbation / fresh) plus: swap words shared with dev2, and a
    swap word repeated inside dev3.
    """
    rows = load_dev3() if rows is None else rows
    out = {k: list(v) for k, v in _dev2_problems(rows).items()}
    dev2_words: set[str] = set()
    for r in load_dev2():
        dev2_words |= swapped_in(r)
    seen = Counter(w for r in rows for w in swapped_in(r))
    for r in rows:
        probs = [f"shared_dev2:{t}" for t in sorted(swapped_in(r) & dev2_words)]
        probs += [f"repeated_swap:{t}" for t in sorted(w for w in swapped_in(r) if seen[w] > 1)]
        if probs:
            out.setdefault(r["id"], []).extend(probs)
    return out


def summary(rows: list[dict] | None = None) -> dict:
    rows = load_dev3() if rows is None else rows
    sp = split_dev3(rows)
    return {
        h: dict(sorted(Counter(r["expect_decision"] for r in rows if sp[r["id"]] == h).items()))
        for h in HALVES
    }

