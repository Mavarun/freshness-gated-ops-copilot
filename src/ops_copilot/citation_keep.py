"""Citation-aware keep count, pre-registered 2026-11-11 before dev9 is used.

The Nov 9 and Nov 10 protocols counted *decisions*: a row the shipped default answers and
an arm refuses was a lost answer. The Nov 10 post-hoc showed why that is wrong for
``d6-06`` (``Who is the first on-call right now?``): the shipped default answers it from the
latency runbook (``first`` matches ``as a first step``), so refusing it is a fix, not a
loss. This module counts *citations* as well, and its rules are frozen here, before any
config is scored on dev9, so a later confirm cannot pick the rule after seeing results.

Right evidence for a row:

- rows derived from a golden question (``source_index``): the answer cites every
  document the shipped default cites for that clean golden question (the Nov 10 post-hoc
  rule; extra citations are allowed);
- dev9 wordy rows: the answer cites at least one document of the row's hand-written list
  in ``data/eval/nonkey_dev9_docs.json`` (written from the corpus text only, no config run
  on dev9);
- any other row: unknown (counted under decisions only, reported separately).

Counts against the shipped default (``citation_counts``):

- ``lost``: shipped answers from the right evidence, the arm does not answer;
- ``fixed``: shipped answers from the wrong evidence, the arm does not answer (not a loss);
- ``new_wrong``: the arm answers from the wrong evidence where the shipped default did not
  answer from the wrong evidence (a new wrong-evidence answer);
- ``unknown_lost``: rows with no evidence label the arm stops answering (decision count).

Pre-registered use on dev9 (next non-key confirm): the lost-row budget applies to
``lost + unknown_lost`` (still ``MAX_LOST_CONFIRM`` = 2), ``fixed`` rows are not losses,
and any ``new_wrong`` row blocks shipping. The decision-only count is still reported next
to it.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Sequence

ROOT = Path(__file__).resolve().parents[2]
DEV9_DOCS_FILE = ROOT / "data" / "eval" / "nonkey_dev9_docs.json"
DEV9_MAX_LOST = 2


def load_dev9_docs(path: str | Path | None = None) -> dict[str, frozenset[str]]:
    raw = json.loads(Path(path or DEV9_DOCS_FILE).read_text(encoding="utf-8"))
    return {k: frozenset(v) for k, v in raw["docs"].items()}


def evidence_ok(bot, row: dict, golden: Sequence[dict], labels: dict[str, frozenset[str]],
                result=None) -> bool | None:
    """True / False when ``bot`` answers ``row`` from the right / wrong evidence; None if unanswered or unlabelled."""
    res = result if result is not None else bot.ask(row["query"])
    if res.decision.value != "ANSWER":
        return None
    cited = set(res.cited_ids)
    if row["id"] in labels:
        return bool(cited & labels[row["id"]])
    if "source_index" in row:
        src = bot.ask(golden[int(row["source_index"])]["query"])
        if src.decision.value != "ANSWER":
            return None
        return set(src.cited_ids) <= cited
    return None


def citation_counts(arm, ref, rows: Sequence[dict], golden: Sequence[dict],
                    labels: dict[str, frozenset[str]] | None = None) -> dict:
    """Citation-aware comparison of ``arm`` against the shipped default ``ref`` on ANSWER rows.

    Right evidence is always judged with ``ref``'s citation of the clean source question, so an
    arm cannot change the yardstick it is measured with.
    """
    labels = labels or {}
    out = {"lost": [], "fixed": [], "new_wrong": [], "unknown_lost": [], "decision_lost": []}
    for r in rows:
        if r.get("expect_decision") != "ANSWER":
            continue
        a, b = arm.ask(r["query"]), ref.ask(r["query"])
        ref_ok = evidence_ok(ref, r, golden, labels, result=b)
        a_ans, b_ans = a.decision.value == "ANSWER", b.decision.value == "ANSWER"
        if b_ans and not a_ans:
            out["decision_lost"].append(r["id"])
            if ref_ok is True:
                out["lost"].append(r["id"])
            elif ref_ok is False:
                out["fixed"].append(r["id"])
            else:
                out["unknown_lost"].append(r["id"])
        if a_ans:
            arm_ok = evidence_ok(ref, r, golden, labels, result=a)
            if arm_ok is False and ref_ok is not False:
                out["new_wrong"].append(r["id"])
    out["budget_lost"] = len(out["lost"]) + len(out["unknown_lost"])
    return out


def dev9_ships_citation_rule(counts: dict) -> bool:
    """Pre-registered dev9 rule: budget on right-evidence + unlabelled losses, no new wrong evidence."""
    return counts["budget_lost"] <= DEV9_MAX_LOST and not counts["new_wrong"]
