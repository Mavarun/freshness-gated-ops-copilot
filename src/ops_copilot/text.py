"""Shared tokenization for retrieval, grounding, and extractive answers."""

from __future__ import annotations

import re
from collections import Counter

TOKEN_RE = re.compile(r"[a-z0-9][a-z0-9_\-]{1,}", re.I)
SENTENCE_RE = re.compile(r"(?<=[.!?])\s+")

STOPWORDS = frozenset(
    {
        "a",
        "an",
        "and",
        "are",
        "as",
        "at",
        "be",
        "by",
        "do",
        "for",
        "from",
        "how",
        "i",
        "in",
        "is",
        "it",
        "of",
        "on",
        "or",
        "our",
        "the",
        "to",
        "was",
        "we",
        "what",
        "when",
        "where",
        "which",
        "who",
        "will",
        "with",
        "you",
        "your",
        "this",
        "that",
        "these",
        "those",
        "current",
        "currently",
        "please",
        "me",
        "my",
        "now",
        "right",
        "does",
        "did",
        "should",
        "can",
        "about",
        "into",
        "many",
        "much",
        "some",
        "any",
        "also",
        "just",
        "still",
        "running",
        "run",
        "configured",
        "using",
        "used",
        "get",
        "got",
        "tell",
        "show",
        "give",
        "need",
        "needs",
        "recommend",
        "recommended",
        "recommends",
        "setting",
        "settings",
        "enabled",
    }
)


def tokenize(text: str) -> list[str]:
    """Lowercased word tokens, including short identifiers like p99."""
    return [m.group(0).lower() for m in TOKEN_RE.finditer(text or "")]


def content_tokens(text: str) -> list[str]:
    """Tokens with stopwords and 1-char noise removed."""
    out: list[str] = []
    for tok in tokenize(text):
        if tok in STOPWORDS:
            continue
        if len(tok) < 2:
            continue
        out.append(tok)
    return out


def split_sentences(text: str) -> list[str]:
    parts = [p.strip() for p in SENTENCE_RE.split((text or "").strip()) if p.strip()]
    return parts or ([text.strip()] if text and text.strip() else [])


def token_set(text: str) -> set[str]:
    return set(content_tokens(text))


def idf_map(docs_tokens: list[list[str]]) -> dict[str, float]:
    """Smoothed IDF used by the grounding gate (unseen query tokens score high)."""
    import math

    n = max(len(docs_tokens), 1)
    df: Counter[str] = Counter()
    for toks in docs_tokens:
        df.update(set(toks))
    return {t: math.log((n - c + 0.5) / (c + 0.5) + 1.0) for t, c in df.items()}


def fold_token(token: str) -> str:
    """Light plural fold so password/passwords and replica/replicas match."""
    if len(token) > 4 and token.endswith("s") and not token.endswith(("ss", "us", "is")):
        return token[:-1]
    return token


def match_tokens(tokens: list[str]) -> set[str]:
    """Token set plus one-step plural/singular variants for overlap checks."""
    out: set[str] = set(tokens)
    for tok in tokens:
        folded = fold_token(tok)
        out.add(folded)
        if folded == tok:
            out.add(tok + "s")
    return out
