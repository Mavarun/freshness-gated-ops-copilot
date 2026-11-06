"""Verified "did you mean" rewrites for grounding refusals (no lexicon, no model).

Held-out ANSWER has been 0 of 9 for weeks because every route to understanding a
held-out word (``lag`` for ``latency``) needs a resource that knows the pair, and
hand-written resources may not contain held-out words. This module does not try to
*understand* the word. When a query is refused as ungrounded with ``missing_terms``,
it proposes rewrites that swap each missing term for a word the closest retrieved
passages actually use, and keeps a rewrite only when the rewritten query passes
every gate (``ANSWER``). The user picks one; the copilot never answers the original
query on its own, so the decision on the original row never changes.

Candidate words come only from the retrieved chunks of the refused query:

- content tokens (no stop/filler words, no identifiers, alphabetic, len >= 3)
  that are not already in the query;
- ranked by ``rank``: ``idf`` (smoothed corpus IDF, summed over the top-k chunks
  that hold the word, weighted 1/rank of the chunk), ``first`` (order of first
  appearance in the top chunk, then the next chunk) or ``context`` (per missing
  term: how many of the term's query neighbours, within ``window`` content tokens,
  sit within ``window`` tokens of the candidate in a retrieved chunk; ``idf`` breaks
  ties). ``context`` is the only rank that looks at *where* the missing word sat:
  ``error ___`` prefers ``budget`` because a chunk says ``error budget``;
- capped at ``max_candidates`` per missing term.

With two missing terms, single swaps are tried first; pairs of candidates are only
tried when no single swap verifies and ``max_pairs`` > 0. ``allow_drop`` also tries
deleting a missing term (off by default: dropping a term is how a trap such as
"what colour is the flag" turns into an answerable question).

Each verified rewrite is checked with a fresh ``Copilot`` that shares the config,
so session ledgers and pending writes from the caller are never touched.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from itertools import product

from ops_copilot.text import NON_SALIENT, fold_token, idf_map, is_identifier, tokenize

_WORD = re.compile(r"[A-Za-z][A-Za-z0-9_\-']*")


@dataclass(frozen=True)
class SuggestConfig:
    rank: str = "idf"  # idf | first
    top_chunks: int = 3
    max_candidates: int = 6
    max_pairs: int = 0
    allow_drop: bool = False
    max_suggestions: int = 3
    window: int = 2


@dataclass
class Rewrite:
    query: str
    swaps: tuple[tuple[str, str], ...]  # (missing term, replacement; "" = dropped)
    cited_ids: list[str] = field(default_factory=list)

    def as_dict(self) -> dict:
        return {
            "query": self.query,
            "swaps": [list(s) for s in self.swaps],
            "cited_ids": list(self.cited_ids),
        }


def _corpus_idf(bot) -> dict[str, float]:
    cached = getattr(bot, "_rewrite_idf", None)
    if cached is None:
        chunks = getattr(bot, "chunks", None) or getattr(bot.retriever, "chunks", [])
        cached = idf_map([tokenize(c.text) for c in chunks])
        bot._rewrite_idf = cached
    return cached


def _eligible(tok: str, query_folded: set[str]) -> bool:
    return (
        tok.isalpha()
        and len(tok) >= 3
        and tok not in NON_SALIENT
        and not is_identifier(tok)
        and fold_token(tok) not in query_folded
    )


def candidate_words(result, bot, cfg: SuggestConfig) -> list[str]:
    """Replacement words drawn from the refused query's retrieved chunks."""
    query_folded = {fold_token(t) for t in tokenize(result.query)}
    chunks = list(result.retrieved)[: cfg.top_chunks]
    if cfg.rank == "first":
        out: list[str] = []
        for ch in chunks:
            for tok in tokenize(ch.text):
                if _eligible(tok, query_folded) and tok not in out:
                    out.append(tok)
        return out
    if cfg.rank not in ("idf", "context"):
        raise ValueError(f"unknown rank {cfg.rank!r}")
    idf = _corpus_idf(bot)
    score: dict[str, float] = {}
    for r, ch in enumerate(chunks, start=1):
        for tok in set(tokenize(ch.text)):
            if _eligible(tok, query_folded):
                score[tok] = score.get(tok, 0.0) + idf.get(tok, 0.0) / r
    return sorted(score, key=lambda t: (-score[t], t))


def _content(tokens: list[str]) -> list[str]:
    return [t for t in tokens if t not in NON_SALIENT]


def query_neighbours(query: str, term: str, window: int) -> set[str]:
    """Content tokens within ``window`` positions of ``term`` in the query."""
    toks = _content(tokenize(query))
    target = fold_token(term.lower())
    out: set[str] = set()
    for i, t in enumerate(toks):
        if fold_token(t) == target:
            lo, hi = max(0, i - window), min(len(toks), i + window + 1)
            out.update(fold_token(x) for x in toks[lo:hi] if fold_token(x) != target)
    return out


def context_scores(result, term: str, words: list[str], cfg: SuggestConfig) -> dict[str, int]:
    """Neighbour overlap of each candidate word with ``term``'s query context."""
    nb = query_neighbours(result.query, term, cfg.window)
    score = {w: 0 for w in words}
    if not nb:
        return score
    for ch in list(result.retrieved)[: cfg.top_chunks]:
        toks = _content(tokenize(ch.text))
        folded = [fold_token(t) for t in toks]
        for i, t in enumerate(toks):
            if t in score:
                lo, hi = max(0, i - cfg.window), min(len(toks), i + cfg.window + 1)
                score[t] += len(nb & set(folded[lo:i] + folded[i + 1 : hi]))
    return score


def ranked_for_term(result, bot, term: str, cfg: SuggestConfig) -> list[str]:
    """Candidate replacements for one missing term, best first."""
    if cfg.rank != "context":
        return candidate_words(result, bot, cfg)[: cfg.max_candidates]
    base = candidate_words(result, bot, SuggestConfig(rank="idf", top_chunks=cfg.top_chunks))
    order = {w: i for i, w in enumerate(base)}
    ctx = context_scores(result, term, base, cfg)
    return sorted(base, key=lambda w: (-ctx[w], order[w]))[: cfg.max_candidates]


def swap_word(query: str, term: str, replacement: str) -> str | None:
    """Replace the first query word whose folded form equals ``term``."""
    target = fold_token(term.lower())
    for m in _WORD.finditer(query):
        if fold_token(m.group(0).lower()) == target:
            head, tail = query[: m.start()], query[m.end() :]
            if not replacement:
                return re.sub(r"\s{2,}", " ", (head + tail)).strip()
            return head + replacement + tail
    return None


def suggest_rewrites(result, bot, cfg: SuggestConfig | None = None, verifier=None) -> list[Rewrite]:
    """Verified rewrites for a REFUSE_UNGROUNDED ``result`` (empty list otherwise)."""
    cfg = cfg or SuggestConfig()
    expl = result.explanation or {}
    if result.decision.value != "REFUSE_UNGROUNDED":
        return []
    missing = [t for t in expl.get("missing_terms") or [] if swap_word(result.query, t, "x")]
    if not missing:
        return []
    if verifier is None:
        from ops_copilot.pipeline import Copilot

        verifier = Copilot(config=bot.config)
    drop = [""] if cfg.allow_drop else []
    options_for = {t: ranked_for_term(result, bot, t, cfg) + drop for t in missing}

    def verify(swaps: tuple[tuple[str, str], ...]) -> Rewrite | None:
        q = result.query
        for term, rep in swaps:
            q2 = swap_word(q, term, rep)
            if q2 is None:
                return None
            q = q2
        r = verifier.ask(q)
        if r.decision.value == "ANSWER":
            return Rewrite(query=q, swaps=swaps, cited_ids=list(r.cited_ids))
        return None

    out: list[Rewrite] = []
    for term in missing:
        for rep in options_for[term]:
            rw = verify(((term, rep),))
            if rw:
                out.append(rw)
    if not out and cfg.max_pairs > 0 and len(missing) >= 2:
        tried = 0
        a, b = missing[:2]
        for ra, rb in product(options_for[a], options_for[b]):
            if ra == rb or tried >= cfg.max_pairs:
                continue
            tried += 1
            rw = verify(((a, ra), (b, rb)))
            if rw:
                out.append(rw)
    return out[: cfg.max_suggestions]
