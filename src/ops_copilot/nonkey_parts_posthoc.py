"""Post-hoc reading of the compound-parts calibration (2026-11-10). Selects nothing.

The calibration picked no arm (every parts arm loses 3 rows against a budget of 2), so the
dev9 confirm was not run and that call stands. This module only explains the 3 rows the
parts arms still lose, so the next slice starts from facts. For each lost row it asks:

- which word the non-key rule named;
- did the *shipped* default cite (at least) the documents it cites for the clean question
  the row was derived from (``source_index`` into the golden set)? A row answered without
  the source's document was a wrong-evidence answer, so refusing it is not a real loss.
  Extra citations alongside the source's document still count as the right evidence.
  dev8 rows have no source question; they are reported as ``n/a``.
"""

from __future__ import annotations

from typing import Sequence


def same_source_doc(bot, query: str, source_query: str | None) -> bool | None:
    """True when ``bot`` cites every document for ``query`` that it cites for its clean source."""
    if source_query is None:
        return None
    a = bot.ask(query)
    b = bot.ask(source_query)
    if a.decision.value != "ANSWER" or b.decision.value != "ANSWER":
        return None
    return set(b.cited_ids) <= set(a.cited_ids)


def read_lost(bot, arm_bot, row: dict, golden: Sequence[dict]) -> dict:
    """One lost row: the named word(s), the shipped citation and whether it matches the source's."""
    q = row["query"]
    src = golden[int(row["source_index"])]["query"] if "source_index" in row else None
    ref = bot.ask(q)
    res = arm_bot.ask(q)
    same = same_source_doc(bot, q, src)
    return {
        "id": row["id"],
        "query": q,
        "source_query": src,
        "words": list(res.grounding.nonkey_unsupported) if res.grounding else [],
        "shipped_cited": list(ref.cited_ids),
        "source_cited": list(bot.ask(src).cited_ids) if src else [],
        "same_doc_as_source": same,
        "reading": ("wrong-evidence answer" if same is False
                    else "genuine loss" if same else "no source question"),
    }
