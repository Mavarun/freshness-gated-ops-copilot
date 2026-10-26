"""Sixth eval set (``dev6``, 48 rows): a single-use confirm set, never tuned on.

Why it exists: the 2026-10-25 re-run of the word-meaning Datamuse grid on the
null-test default found a candidate (rank <= 100, one neighbour, context >= 2,
sense >= 0.30; 98 vs 88 of 171 calibration rows), but dev5 ``confirm`` had
just been spent by the null-control test, so nothing unseen was left to
confirm it. ``data/eval/synonym_dev6.jsonl`` was written by hand on
2026-10-26, before the Datamuse, WordNet or counter-fitted tables were queried
for any of its words and before any config was run on it.

Unlike dev2..dev5 there is **no tune half**: the arm to confirm is already
frozen (``datamuse_dev6.py``), so every row is a confirm row and the set is
spent after one scored run of that arm. Only the shipped default may be
scored on it before then (the CI report).

Contents (45 rows):

- 33 one-swap paraphrases of golden queries (24 ANSWER, 5 REFUSE_STALE,
  4 REFUSE_UNGROUNDED), golden label kept, ops-style or everyday rewording
  (``latency -> lateness``, ``on-call -> duty-engineer``, ``replicas ->
  workers``, ``freeze -> hold``, ``runbook -> sop``, ``restart -> reload``);
- 9 new absent-topic traps. Seven are **word-sense traps**: one unknown word
  that a dictionary relates to a corpus word in another sense (a national
  flag's ``country``, a theatre ``rehearsal`` next to ``production``, a
  ``battery`` next to ``remaining ... budget``, ``passengers`` next to
  ``running``, ``marital`` status, a swimming ``pool``'s water temperature, a
  ``crop rotation``); two are off-topic (REFUSE_NO_EVIDENCE);
- 3 canary / PII / write paraphrases.

How the words were picked (disclosed): the first two hand-written drafts used
the obvious ops synonyms (``reboot``, ``bounce``, ``instances``, ``delay``,
``health``, ``playbook``, ...). The guard below rejected 38 and then 35 of
their rows: those words are held-out words or were already used by
dev..dev5. That is a finding in itself: the README's open ops synonyms are
the held-out set, so dev6 cannot contain them. Replacements were drawn from
hand-written candidate lists per golden slot, screened **only** by this
guard (own eval files and the held-out list); no Datamuse, WordNet or vector
table was consulted, and no config was run on any row.

Every refusal row is **must-refuse** (``must_refuse_rows``).

Guards are dev5's plus dev5 swap words (``vocabulary_problems``): no held-out
word in any query, no swap word shared with dev / held-out / perturbation /
fresh / dev2 / dev3 / dev4 / **dev5**, no swap word repeated inside dev6.
"""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

from ops_copilot.synonym_dev2 import swapped_in
from ops_copilot.synonym_dev4 import OPENING
from ops_copilot.synonym_dev5 import load_dev5
from ops_copilot.synonym_dev5 import vocabulary_problems as _dev5_problems

DEV6_PATH = Path(__file__).resolve().parents[2] / "data" / "eval" / "synonym_dev6.jsonl"


def load_dev6(path: str | Path | None = None) -> list[dict]:
    src = Path(path) if path else DEV6_PATH
    return [json.loads(ln) for ln in src.read_text(encoding="utf-8").splitlines() if ln.strip()]


def must_refuse_rows(rows: list[dict]) -> list[dict]:
    """Rows whose expected decision is a refusal: they may never open."""
    return [r for r in rows if r["expect_decision"] not in OPENING]


def vocabulary_problems(rows: list[dict] | None = None) -> dict[str, list[str]]:
    """Row id -> problems (must be empty): dev5's guard plus dev5 swap words."""
    rows = load_dev6() if rows is None else rows
    out = {k: [p for p in v if not p.startswith("repeated_swap:")] for k, v in _dev5_problems(rows).items()}
    out = {k: v for k, v in out.items() if v}
    dev5_words: set[str] = set()
    for r in load_dev5():
        dev5_words |= swapped_in(r)
    seen = Counter(w for r in rows for w in swapped_in(r))
    for r in rows:
        probs = [f"shared_dev5:{t}" for t in sorted(swapped_in(r) & dev5_words)]
        probs += [f"repeated_swap:{t}" for t in sorted(w for w in swapped_in(r) if seen[w] > 1)]
        if probs:
            out.setdefault(r["id"], []).extend(probs)
    return out


def summary(rows: list[dict] | None = None) -> dict[str, int]:
    rows = load_dev6() if rows is None else rows
    return dict(sorted(Counter(r["expect_decision"] for r in rows).items()))
