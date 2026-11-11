"""Tenth eval set (``dev10``): fresh one-swap paraphrases, written 2026-11-11 before any arm was scored.

Why it exists: the resource-agreement backoff (``resource_agreement.py``) needs a confirm
set no config has seen. dev9 stays reserved for the non-key line (its citation-aware keep
count is pre-registered in ``citation_keep.py``), and dev2-dev8 are spent or tuned on.

Contents (26 rows): 15 one-swap paraphrases of golden ANSWER queries (golden label kept),
7 one-swap paraphrases of golden refusals (2 stale, 3 ungrounded, 2 no-evidence) and 4
new attribute-style traps on known pages (``temperature``, ``landlord``, ``passengers``,
``chlorine``). Every refusal is must-refuse.

How the words were picked (disclosed): three drafts. Replacement words were hand-written
per golden slot and screened only by the guard below; the first draft lost 28 of 30 rows
to it (``delay``, ``copies``, ``occupancy`` ... were all used by dev2-dev7), the second 23.
For the third, up to six hand-written candidates per slot were screened in order and the
first that passed was kept, then 8 rows were dropped by hand because the surviving word
was not a fair paraphrase (``exhaustion`` / ``employment`` for utilization, ``mistake``
budget, ``berth``, ``care`` window, ``fettle``, ``contemporary``) or no candidate passed
(replicas). No Datamuse, WordNet, counter-fitted, Wiktionary or tag table was consulted
for dev10 words, and no config was run on any dev10 row before this file was committed.
Before writing dev10 the five resources *were* probed on the dev split's pairs (not on
held-out pairs) to see whether agreement had any coverage; that is disclosed in the
protocol docstring.

Guards (``vocabulary_problems``): dev7's guard plus dev7 swap words: no held-out word in
any query; no swap word shared with dev / held-out / perturbation / fresh / dev2..dev7;
no swap word repeated inside dev10.
"""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

from ops_copilot.synonym_dev2 import swapped_in
from ops_copilot.synonym_dev4 import OPENING
from ops_copilot.synonym_dev7 import load_dev7
from ops_copilot.synonym_dev7 import vocabulary_problems as _dev7_problems

DEV10_PATH = Path(__file__).resolve().parents[2] / "data" / "eval" / "synonym_dev10.jsonl"


def load_dev10(path: str | Path | None = None) -> list[dict]:
    src = Path(path) if path else DEV10_PATH
    return [json.loads(ln) for ln in src.read_text(encoding="utf-8").splitlines() if ln.strip()]


def must_refuse_rows(rows: list[dict]) -> list[dict]:
    return [r for r in rows if r["expect_decision"] not in OPENING]


def vocabulary_problems(rows: list[dict] | None = None) -> dict[str, list[str]]:
    """Row id -> problems (must be empty): dev7's guard plus dev7 swap words."""
    rows = load_dev10() if rows is None else rows
    out = {k: [p for p in v if not p.startswith("repeated_swap:")] for k, v in _dev7_problems(rows).items()}
    out = {k: v for k, v in out.items() if v}
    dev7_words: set[str] = set()
    for r in load_dev7():
        dev7_words |= swapped_in(r)
    seen = Counter(w for r in rows for w in swapped_in(r))
    for r in rows:
        probs = [f"shared_dev7:{t}" for t in sorted(swapped_in(r) & dev7_words)]
        probs += [f"repeated_swap:{t}" for t in sorted(w for w in swapped_in(r) if seen[w] > 1)]
        if probs:
            out.setdefault(r["id"], []).extend(probs)
    return out
