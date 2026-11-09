"""Post-hoc reading of the non-key coverage confirm (2026-11-09). Selects nothing.

The one-shot confirm (``artifacts/nonkey_confirm.json``) is spent and its ship call (off)
stands. This module only explains the record so the next slice starts from facts:

- ``lost_rows``: for every answered row the picked arm lost (calibration and confirm), is
  the missing word a hyphen part of a cited evidence token (``checkout`` inside the pager
  name ``checkout-primary``), i.e. a tokenisation gap rather than a topic change?
- ``topic_traps``: for every dev8 topic trap the shipped default opens, is the trap word
  outside the key half and unsupported (the rule's target) or supported lexically (no
  coverage rule can close it)?
"""

from __future__ import annotations

from ops_copilot.text import content_tokens, fold_token


def cited_text(bot, result) -> str:
    ids = set(result.cited_ids)
    return " ".join(f"{c.title} {c.text}" for c in bot.corpus.chunks if c.chunk_id in ids or c.doc_id in ids)


def hyphen_parts(text: str) -> set[str]:
    """Parts of hyphenated evidence tokens (``checkout-primary`` -> checkout, primary)."""
    out: set[str] = set()
    for tok in content_tokens(text):
        if "-" in tok and not any(ch.isdigit() for ch in tok):
            out |= {fold_token(p) for p in tok.split("-") if p}
    return out


def read_lost(bot, arm_bot, row_id: str, query: str) -> dict:
    """Why ``arm_bot`` refused a row ``bot`` answers: each named word, and whether it is a compound part."""
    ref = bot.ask(query)
    res = arm_bot.ask(query)
    parts = hyphen_parts(cited_text(bot, ref))
    words = list(res.grounding.nonkey_unsupported) if res.grounding else []
    return {"id": row_id, "query": query, "words": words,
            "compound_part": [w for w in words if fold_token(w) in parts]}


def read_trap(bot, arm_bot, row_id: str, query: str) -> dict:
    """How a topic trap the shipped default opens was covered, and whether the arm closes it."""
    res = bot.ask(query)
    keys = set(bot.grounder.key_tokens(query))
    sup_terms = set(res.grounding.overlap_tokens) if res.grounding else set()
    terms = bot.grounder.terms(query)
    missing = [t.token for t in terms if t.token not in sup_terms]
    return {"id": row_id, "query": query, "unsupported": missing,
            "unsupported_nonkey": [w for w in missing if w not in keys],
            "kind": "non-key unsupported" if missing and not set(missing) & keys else "lexical",
            "arm_decision": arm_bot.ask(query).decision.value}
