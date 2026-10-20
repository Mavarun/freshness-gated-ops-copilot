"""Post-hoc: does Datamuse ``ml`` cover the noun swaps WordNet could not?

Run after the dev2 confirm decision (it changes nothing and selects nothing).
For every single-word swap row of a hand-written set (``latency -> delay``)
whose original is a corpus word and whose swapped-in word is not, it looks up
the Datamuse rank of the swapped-in word in the original word's ``ml`` list
(committed table, ungated) and buckets the row under an arm:

- ``no_link``: the original's top-100 list does not hold the swapped-in word;
- ``outside_gate``: a link exists but the gate drops it (rank cut-off, noun
  tag) or other corpus words fill the neighbour slots first;
- ``mapped_still_wrong``: the gate maps the word onto the original, yet the
  decision is still wrong (retrieval, grounding, another gate);
- ``correct``: the row is right under the arm. ``right_without_link`` marks a
  correct row the arm fixed although the gate never maps onto the original
  (fixed via a different, usually wrong-sense, corpus word).

It also reports, for the same rows, the WordNet bucket from
``wordnet_coverage`` so the two resources can be compared row by row.
"""

from __future__ import annotations

from collections import Counter

from ops_copilot.datamuse_senses import DatamuseSense
from ops_copilot.text import fold_token
from ops_copilot.wordnet_coverage import swap_pairs

BUCKETS = ("no_link", "outside_gate", "mapped_still_wrong", "correct", "not_applicable")


def link_rank(backoff: DatamuseSense, new: str, orig: str) -> int | None:
    """Rank of ``new`` in ``orig``'s ml list (ungated), or None."""
    for word, rank, _noun, _d in backoff.table.neighbours.get(new, ()):
        if fold_token(word) == fold_token(orig):
            return rank
    return None


def _mapped(backoff: DatamuseSense, new: str) -> list[str]:
    was = backoff.suspend_unknown
    backoff.suspend_unknown = False
    try:
        return [n.word for n in backoff.neighbours(new)]
    finally:
        backoff.suspend_unknown = was


def bucket_row(row: dict, decision: str, off_decision: str, backoff: DatamuseSense) -> dict:
    vocab_f = {fold_token(w) for w in backoff.source_vocab}
    pairs = [(o, n) for o, n in swap_pairs(row) if fold_token(o) in vocab_f and fold_token(n) not in vocab_f]
    if len(pairs) != 1:
        b = "correct" if decision == row["expect_decision"] else "not_applicable"
        return {"bucket": b, "pairs": pairs}
    orig, new = pairs[0]
    rank = link_rank(backoff, new, orig)
    mapped = _mapped(backoff, new)
    hit = fold_token(orig) in {fold_token(w) for w in mapped}
    out = {"pairs": pairs, "rank": rank, "gate_maps_to": mapped}
    if decision == row["expect_decision"]:
        fixed = off_decision != row["expect_decision"]
        return {**out, "bucket": "correct", "right_without_link": bool(fixed and not hit)}
    if rank is None:
        return {**out, "bucket": "no_link"}
    if not hit:
        return {**out, "bucket": "outside_gate"}
    return {**out, "bucket": "mapped_still_wrong"}


def coverage(
    rows: list[dict], decisions: dict[str, str], off_decisions: dict[str, str], backoff: DatamuseSense
) -> dict:
    per_row = {
        r["id"]: bucket_row(r, decisions[r["id"]], off_decisions[r["id"]], backoff)
        for r in rows
        if "swap" in r
    }
    counts = Counter(v["bucket"] for v in per_row.values())
    ranks = [v["rank"] for v in per_row.values() if v.get("pairs") and len(v["pairs"]) == 1]
    return {
        "counts": {b: counts.get(b, 0) for b in BUCKETS},
        "n_right_without_link": sum(bool(v.get("right_without_link")) for v in per_row.values()),
        "n_single_swaps": len(ranks),
        "n_linked_rank_le": {k: sum(r is not None and r <= k for r in ranks) for k in (10, 20, 50, 100)},
        "rows": per_row,
    }
