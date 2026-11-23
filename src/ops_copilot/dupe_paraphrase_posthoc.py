"""Post-hoc reading of the duplicate-paraphrase calibration (2026-11-23). Selects nothing.

No arm was eligible, so the confirm was not run and dev10 stays unseen; that call stands.
This module explains the result so the next slice starts from facts:

- ``pair_coverage``: for each single-word pair of the frozen synonym split
  (``key -> word``), whether the gold key word passes the strict / loose gates for the
  replacement word, and whether it is the top gate-passing candidate. Held-out pairs are
  read only because the go / no-go is decided (the repo's rule since Oct 7).
- ``raw_row``: the table's numbers for a pair, gate or no gate (for the ops pairs the
  README keeps naming), and whether the gold key word is a corpus word at all (the noun
  slot can only map onto corpus words).
- ``new_swap_passes``: the random swaps an arm answers that the shipped default refused,
  with the corpus word the table mapped the swapped-in word onto.
"""

from __future__ import annotations

from collections import Counter
from typing import Iterable

from ops_copilot.text import fold_token


def single_word_pairs(pairs: Iterable[str]) -> list[tuple[str, str]]:
    out = []
    for p in pairs:
        key, word = (x.strip().lower() for x in p.split("->", 1))
        if " " not in key and " " not in word and "-" not in key and "-" not in word:
            out.append((key, word))
    return out


def _same(a: str, b: str) -> bool:
    return fold_token(a) == fold_token(b)


def raw_row(table, key: str, word: str) -> dict | None:
    for other, g2, cross, same in table.get(word):
        if _same(other, key):
            return {"g2": g2, "cross": cross, "same": same}
    return None


def pair_coverage(senses: dict, table, pairs: Iterable[str]) -> dict:
    """Per pair: in table at all, and per gate setting: gold passes / is top candidate."""
    rows, c = [], Counter()
    for key, word in single_word_pairs(pairs):
        any_sense = next(iter(senses.values()))
        row = {"pair": f"{key}->{word}", "raw": raw_row(table, key, word),
               "key_in_corpus": any_sense._in_corpus(fold_token(key)) is not None or key in any_sense.corpus_words}
        c["pairs"] += 1
        c["in_table"] += row["raw"] is not None
        c["in_table_key_in_corpus"] += row["raw"] is not None and row["key_in_corpus"]
        for name, sense in senses.items():
            cands = [w for w, *_ in sense.candidates(word)]
            gold = any(_same(w, key) for w in cands)
            top = cands[0] if cands else None
            row[name] = {"gold_passes": gold, "top": top, "top_is_gold": top is not None and _same(top, key)}
            c[f"{name}_gold_passes"] += gold
            c[f"{name}_top_is_gold"] += row[name]["top_is_gold"]
            c[f"{name}_top_is_wrong"] += top is not None and not row[name]["top_is_gold"]
        rows.append(row)
    return {"summary": dict(c), "rows": rows}


def new_swap_passes(arm_passes: list[dict], ref_passes: list[dict], sense) -> list[dict]:
    """Swaps the arm answers and the reference refuses, with the table's mapping of the word."""
    ref = {(p["row"], p["term"], p["word"]) for p in ref_passes}
    out = []
    for p in arm_passes:
        if (p["row"], p["term"], p["word"]) in ref:
            continue
        cands = sense.candidates(p["word"])
        out.append({"row": p["row"], "term": p["term"], "word": p["word"],
                    "mapped": cands[0][0] if cands else None,
                    "mapped_is_term": bool(cands) and _same(cands[0][0], p["term"])})
    return out
