"""Post-hoc reading of the resource-agreement calibration (2026-11-11). Selects nothing.

No arm was eligible, so the confirm was not run and dev10 stays unseen; that call stands.
This module explains the result so the next slice starts from facts:

- ``pair_coverage``: for each single-word synonym pair of the frozen split (``key -> word``),
  how many resources propose the gold key word for the replacement word, and whether the
  top agreed candidate is the gold word. Held-out pairs are read here only because the
  go / no-go is already decided (the repo's rule since the Oct 7 lexicon slice); dev pairs
  are shown next to them.
- ``gained_rows``: which query word the agreement mapped, onto what, for each calibration
  row a gaining arm newly answers.
"""

from __future__ import annotations

from collections import Counter
from typing import Iterable

from ops_copilot.text import fold_token


def single_word_pairs(pairs: Iterable[str]) -> list[tuple[str, str]]:
    out = []
    for p in pairs:
        key, word = (x.strip().lower() for x in p.split("->", 1))
        if " " not in key and " " not in word:
            out.append((key, word))
    return out


def pair_coverage(sense, pairs: Iterable[str]) -> dict:
    """Votes for the gold key word and the top agreed candidate per single-word pair."""
    rows = []
    for key, word in single_word_pairs(pairs):
        votes = sense.votes(word)
        gold = max((n for w, n in votes.items() if fold_token(w) == fold_token(key)), default=0)
        ranked = sorted(((-n, w) for w, n in votes.items()))
        top = ranked[0][1] if ranked else None
        top_n = -ranked[0][0] if ranked else 0
        rows.append({"pair": f"{key}->{word}", "gold_votes": gold, "top": top, "top_votes": top_n,
                     "top_is_gold": top is not None and fold_token(top) == fold_token(key)})
    c = Counter()
    for r in rows:
        c["pairs"] += 1
        c["gold_2plus"] += r["gold_votes"] >= 2
        c["gold_3plus"] += r["gold_votes"] >= 3
        c["top2_is_gold"] += r["top_votes"] >= 2 and r["top_is_gold"]
        c["top2_is_wrong"] += r["top_votes"] >= 2 and not r["top_is_gold"]
    return {"summary": dict(c), "rows": rows}


def mapped_words(grounder, query: str) -> list[dict]:
    """Query terms whose kind came from the noun slot (the agreement), with their alts."""
    return [{"token": t.token, "kind": t.kind, "alts": sorted(t.alts - {t.token})}
            for t in grounder.terms(query) if t.kind not in ("known", "identifier", "typo", "synonym", "unknown")]
