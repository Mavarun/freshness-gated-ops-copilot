"""Post-hoc: is a missed noun swap a WordNet coverage gap or a gate / pipeline gap?

Run after the dev2 confirm decision (it changes nothing and selects nothing).
For every swap row of a hand-written set (``latency -> delay``) it looks up
the WordNet relation from the swapped-in word back to the original word in
the committed neighbour table, then buckets the row:

- ``no_link``: WordNet relates the pair by no path <= 2 (or the swapped-in
  word is not a WordNet noun at all): a *resource* gap;
- ``outside_gate``: a link exists but the gate drops it (path, sibling
  fan-out, sense rank) or it is not the first neighbour kept;
- ``mapped_still_wrong``: the gate maps the word onto the original, yet the
  decision is still wrong: a *pipeline* gap (retrieval, grounding, another
  unknown word);
- ``correct``: the row is right under the arm.

Only swaps whose original is a single corpus word are bucketed; the rest are
``not_applicable`` (verbs, multi-word swaps, non-corpus originals).
"""

from __future__ import annotations

from collections import Counter

from ops_copilot.text import fold_token, tokenize
from ops_copilot.wordnet_senses import WordNetNounSense, noun_base_forms

BUCKETS = ("no_link", "outside_gate", "mapped_still_wrong", "correct", "not_applicable")


def swap_pairs(row: dict) -> list[tuple[str, str]]:
    out = []
    for part in str(row.get("swap", "")).split(","):
        if "->" not in part:
            continue
        a, b = part.split("->", 1)
        ta, tb = tokenize(a), tokenize(b)
        if len(ta) == 1 and len(tb) == 1:
            out.append((ta[0], tb[0]))
    return out


def link(backoff: WordNetNounSense, new: str, orig: str) -> dict | None:
    """Best table row from ``new`` to ``orig`` (morphy fallback), ungated."""
    table = backoff.table.neighbours
    keys = [new] + [b for b in noun_base_forms(new, table) if b != new]
    for k in keys:
        for word, rel, path, fan, rank in table.get(k, ()):
            if fold_token(word) == fold_token(orig):
                return {"lemma": k, "relation": rel, "path": path, "fan_out": fan, "sense_rank": rank}
    return None


def bucket_row(row: dict, decision: str, backoff: WordNetNounSense) -> dict:
    pairs = swap_pairs(row)
    vocab = backoff.source_vocab
    vocab_f = {fold_token(w) for w in vocab}
    pairs = [(o, n) for o, n in pairs if fold_token(o) in vocab_f and fold_token(n) not in vocab_f]
    if decision == row["expect_decision"]:
        return {"bucket": "correct", "pairs": pairs}
    if len(pairs) != 1:
        return {"bucket": "not_applicable", "pairs": pairs}
    orig, new = pairs[0]
    lk = link(backoff, new, orig)
    if lk is None:
        return {"bucket": "no_link", "pairs": pairs, "link": None}
    was = backoff.suspend_unknown
    backoff.suspend_unknown = False
    try:
        mapped = [n.word for n in backoff.neighbours(new)]
    finally:
        backoff.suspend_unknown = was
    if fold_token(orig) not in {fold_token(w) for w in mapped}:
        return {"bucket": "outside_gate", "pairs": pairs, "link": lk, "gate_maps_to": mapped}
    return {"bucket": "mapped_still_wrong", "pairs": pairs, "link": lk, "gate_maps_to": mapped}


def coverage(rows: list[dict], decisions: dict[str, str], backoff: WordNetNounSense) -> dict:
    per_row = {r["id"]: bucket_row(r, decisions[r["id"]], backoff) for r in rows if "swap" in r}
    counts = Counter(v["bucket"] for v in per_row.values())
    return {"counts": {b: counts.get(b, 0) for b in BUCKETS}, "rows": per_row}
