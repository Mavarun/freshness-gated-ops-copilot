"""Second calibration set for read-path noun-sense backoffs (``dev2``, 43 rows).

Why it exists: the 15-row dev split (5 ANSWER rows) could not tell fourteen
safe WordNet gates apart (PR #23), and held-out has now been looked at twice
for that family. A gate can only be chosen honestly on rows written *before*
any run of it. ``data/eval/synonym_dev2.jsonl`` was written by hand on
2026-10-19, before the WordNet neighbour table was queried for any of its
words and before any config was run on it.

Contents:

- 29 one-swap paraphrases of golden queries, mostly *noun* swaps
  (``latency -> delay``, ``status -> standing``, ``replicas -> copies``), with
  the golden label kept (20 ANSWER, 6 REFUSE_STALE, 3 REFUSE_UNGROUNDED);
- 8 new absent-topic traps, most with a *single* unknown content word
  (``What is the checkout invoice latency?``), the shape the lone-unknown
  scope is weakest on (README, PR #23 weaknesses);
- 6 canary / PII / write paraphrases, so a backoff that breaks another gate
  shows up here too.

Guards (``vocabulary_problems``, tested in CI):

- no query contains a held-out word of the perturbation split, folded as the
  resource audit folds (``fold_token``);
- no swapped-in word is a dev or held-out word, a replacement word of the
  perturbation synonym map, or a swapped-in word of the fresh set, so the
  sets share no replacement vocabulary.

Split (``split_dev2``): stratified by expected decision, ordered by a salted
SHA-256 of the row id, alternating ``calib`` / ``confirm``. Calibration may
read ``calib`` rows only; ``confirm`` rows are scored once, by the
pre-registered rule in ``wordnet_dev2.py``.
"""

from __future__ import annotations

import hashlib
import json
from collections import defaultdict
from pathlib import Path

from ops_copilot.text import fold_token, tokenize

DEV2_PATH = Path(__file__).resolve().parents[2] / "data" / "eval" / "synonym_dev2.jsonl"
SPLIT_SALT = "dev2-calib-confirm-2026-10-19"
HALVES = ("calib", "confirm")


def load_dev2(path: str | Path | None = None) -> list[dict]:
    src = Path(path) if path else DEV2_PATH
    return [json.loads(ln) for ln in src.read_text(encoding="utf-8").splitlines() if ln.strip()]


def swapped_in(row: dict) -> set[str]:
    """Words a swap row puts into the golden query (empty for new traps)."""
    if "swap" not in row:
        return set()
    out: set[str] = set()
    for part in str(row["swap"]).split(","):
        out |= set(tokenize(part.split("->", 1)[1]))
    return out


def _hash(rid: str) -> str:
    return hashlib.sha256(f"{SPLIT_SALT}:{rid}".encode()).hexdigest()


def split_dev2(rows: list[dict] | None = None) -> dict[str, str]:
    """Row id -> ``calib`` / ``confirm`` (stratified by expected decision)."""
    rows = load_dev2() if rows is None else rows
    by_label: dict[str, list[str]] = defaultdict(list)
    for r in rows:
        by_label[r["expect_decision"]].append(r["id"])
    out: dict[str, str] = {}
    for label in sorted(by_label):
        for i, rid in enumerate(sorted(by_label[label], key=_hash)):
            out[rid] = HALVES[i % 2]
    return out


def half(name: str, rows: list[dict] | None = None) -> list[dict]:
    if name not in HALVES:
        raise ValueError(f"unknown half {name!r}")
    rows = load_dev2() if rows is None else rows
    sp = split_dev2(rows)
    return [r for r in rows if sp[r["id"]] == name]


def vocabulary_problems(rows: list[dict] | None = None) -> dict[str, list[str]]:
    """Row id -> problems (must be empty): held-out words or shared swap vocabulary."""
    from ops_copilot.fresh_synonym_eval import load_fresh, swapped_words
    from ops_copilot.perturb import synonym_pairs
    from ops_copilot.synonym_split import load_split

    rows = load_dev2() if rows is None else rows
    split = load_split()
    held = {fold_token(w) for w in split["heldout_words"]}
    taken = set(split["dev_words"]) | set(split["heldout_words"])
    for _, repl in synonym_pairs():
        taken |= set(tokenize(repl))
    for fr in load_fresh():
        taken |= swapped_words(fr)
    out: dict[str, list[str]] = {}
    for r in rows:
        probs = [f"heldout:{t}" for t in sorted({fold_token(t) for t in tokenize(r["query"])} & held)]
        probs += [f"shared_swap:{t}" for t in sorted(swapped_in(r) & taken)]
        if probs:
            out[r["id"]] = probs
    return out
