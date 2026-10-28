"""Seventh eval set (``dev7``): fresh paraphrases with a tune / confirm split (written 2026-10-28).

Why it exists: dev5 confirm and dev6 are spent, so the credited-word check
(``credit_check.py``) needs paraphrase rows no config has seen, to measure what
the check *costs* on real rewording, and a tune half to choose a setting on.
``data/eval/synonym_dev7.jsonl`` was written by hand on 2026-10-28 before any
config was run on it.

Contents (40 rows): 26 one-swap paraphrases of golden ANSWER queries (golden
label kept), 8 one-swap paraphrases of golden refusals (4 stale, 4
ungrounded), 3 canary / PII / write paraphrases, and 3 new word-sense traps
(``fuel`` budget, ``lifeguard``, ``harvest``). Every refusal is must-refuse.
Split: 22 tune (13 ANSWER) / 18 confirm (13 ANSWER, 5 must-refuse).

How the words were picked (disclosed): candidate replacement words were
hand-written per golden slot and screened **only** by the guard below (three
drafts: 37, then 2, then a handful of rows were rejected and their words
replaced; awkward but grammatical forms such as ``feature-gate`` or ``twins``
were kept rather than consult a table); no
Datamuse, WordNet, counter-fitted or domain-vector table was consulted and
no config was scored on any row before the split was frozen. The open ops
synonyms the README lists (``lag``, ``bounce``, ``reboot``) are held-out words,
so dev7 cannot contain them either.

Guards (``vocabulary_problems``): dev6's guard plus dev6 swap words: no
held-out word in any query; no swap word shared with dev / held-out /
perturbation / fresh / dev2..dev6; no swap word repeated inside dev7.

Split (``split_dev7``): whole source groups move together (a golden query's
paraphrases never straddle halves), balanced per label with a salted hash.
"""

from __future__ import annotations

import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path

from ops_copilot.synonym_dev2 import swapped_in
from ops_copilot.synonym_dev4 import OPENING
from ops_copilot.synonym_dev5 import group_key
from ops_copilot.synonym_dev6 import load_dev6
from ops_copilot.synonym_dev6 import vocabulary_problems as _dev6_problems

DEV7_PATH = Path(__file__).resolve().parents[2] / "data" / "eval" / "synonym_dev7.jsonl"
SPLIT_SALT = "dev7-tune-confirm-2026-10-28"
HALVES = ("tune", "confirm")


def load_dev7(path: str | Path | None = None) -> list[dict]:
    src = Path(path) if path else DEV7_PATH
    return [json.loads(ln) for ln in src.read_text(encoding="utf-8").splitlines() if ln.strip()]


def _hash(key: str) -> str:
    return hashlib.sha256(f"{SPLIT_SALT}:{key}".encode()).hexdigest()


def split_dev7(rows: list[dict] | None = None) -> dict[str, str]:
    """Row id -> ``tune`` / ``confirm``; whole source groups move together."""
    rows = load_dev7() if rows is None else rows
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
    rows = load_dev7() if rows is None else rows
    sp = split_dev7(rows)
    return [r for r in rows if sp[r["id"]] == name]


def must_refuse_rows(rows: list[dict]) -> list[dict]:
    return [r for r in rows if r["expect_decision"] not in OPENING]


def vocabulary_problems(rows: list[dict] | None = None) -> dict[str, list[str]]:
    """Row id -> problems (must be empty): dev6's guard plus dev6 swap words."""
    rows = load_dev7() if rows is None else rows
    out = {k: [p for p in v if not p.startswith("repeated_swap:")] for k, v in _dev6_problems(rows).items()}
    out = {k: v for k, v in out.items() if v}
    dev6_words: set[str] = set()
    for r in load_dev6():
        dev6_words |= swapped_in(r)
    seen = Counter(w for r in rows for w in swapped_in(r))
    for r in rows:
        probs = [f"shared_dev6:{t}" for t in sorted(swapped_in(r) & dev6_words)]
        probs += [f"repeated_swap:{t}" for t in sorted(w for w in swapped_in(r) if seen[w] > 1)]
        if probs:
            out.setdefault(r["id"], []).extend(probs)
    return out


def summary(rows: list[dict] | None = None) -> dict:
    rows = load_dev7() if rows is None else rows
    sp = split_dev7(rows)
    return {h: dict(sorted(Counter(r["expect_decision"] for r in rows if sp[r["id"]] == h).items()))
            for h in HALVES}
