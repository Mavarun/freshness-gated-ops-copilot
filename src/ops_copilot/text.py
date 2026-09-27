"""Shared normalization and tokenization for retrieval, grounding, and gates.

``normalize_text`` is the single entry point every matcher uses before it looks
at a query: BM25, the body TF-IDF hybrid, the title-hash dense stub, the
grounding gate, the write-intent gate, and the PII contact allowlist. Before it
existed each component saw a slightly different string (the dense stub hashed
``p99?`` with the question mark attached, the write gate matched raw case), so
the same question could rank differently depending on where punctuation fell.
"""

from __future__ import annotations

import re
import unicodedata
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
        # Generic function words that carry no ops content. Negations
        # ("not", "no", "never") are deliberately absent: they change meaning.
        "am",
        "been",
        "being",
        "were",
        "has",
        "have",
        "had",
        "its",
        "they",
        "them",
        "their",
        "there",
        "here",
        "if",
        "then",
        "than",
        "so",
        "too",
        "very",
        "may",
        "might",
        "must",
        "shall",
        "would",
        "could",
        "why",
        "whom",
        "whose",
        "us",
    }
)

# Politeness / discourse filler: words people wrap around a question that say
# nothing about *what* is being asked. They are never salient for grounding
# (see grounding.py). Kept separate from STOPWORDS so the list is auditable.
# Overlap note: this is a closed class, so it necessarily covers the words in
# the robustness eval's polite prefixes (perturb._QUESTION_PREFIXES /
# _IMPERATIVE_PREFIXES); robustness.leakage_report() measures that overlap.
FILLER_WORDS = frozenset(
    {
        "hey",
        "hi",
        "hello",
        "team",
        "folks",
        "all",
        "sorry",
        "bother",
        "bothering",
        "but",
        "wondering",
        "wonder",
        "curious",
        "quick",
        "question",
        "kindly",
        "thanks",
        "thank",
        "pls",
        "plz",
        "chance",
        "mind",
        "know",
        "let",
        "like",
        "want",
        "wanted",
        "ask",
        "asking",
        "help",
        "appreciate",
        "anyone",
        "someone",
        "somebody",
        "happen",
        "possibly",
        "maybe",
        "actually",
        "basically",
        "okay",
        "ok",
    }
)

NON_SALIENT = STOPWORDS | FILLER_WORDS

_IDENTIFIER_CHARS = frozenset("-_.")


# Typographic look-alikes folded to ASCII before anything else runs.
_ASCII_FOLD = str.maketrans(
    {
        "\u2018": "'",
        "\u2019": "'",
        "\u201b": "'",
        "\u2032": "'",
        "\u201c": '"',
        "\u201d": '"',
        "\u2010": "-",
        "\u2011": "-",
        "\u2012": "-",
        "\u2013": "-",
        "\u2014": " ",
        "\u2212": "-",
        "\u00a0": " ",
        "\u200b": "",
    }
)
_CONTRACTION_IS = re.compile(
    r"\b(what|where|who|how|when|why|which|that|there|here|it)'s\b"
)
_POSSESSIVE = re.compile(r"'s\b")
# Keep only characters that can live inside a token; ``-_./:@`` survive only
# *between* alphanumerics so identifiers (checkout-api, redis.maxmemory-policy,
# checkout_retry, 18:04) stay intact while stuck-on punctuation ("p99?",
# "(resolved)", "#inc-4821") is stripped.
_NON_TOKEN_CHARS = re.compile(r"[^a-z0-9\-_./:@\s]+")
_EDGE_JOINERS = re.compile(r"(?<![a-z0-9])[\-_./:@]+|[\-_./:@]+(?![a-z0-9])")


def normalize_text(text: str) -> str:
    """Canonical matching form: NFKC + accent strip, lowercase, no loose punctuation.

    Identifier punctuation between alphanumerics is preserved; everything else
    that is not a letter/digit becomes whitespace. Idempotent.
    """
    if not text:
        return ""
    t = unicodedata.normalize("NFKD", text.translate(_ASCII_FOLD))
    t = "".join(ch for ch in t if not unicodedata.combining(ch))
    t = unicodedata.normalize("NFKC", t).lower()
    t = _CONTRACTION_IS.sub(r"\1 is", t)
    t = _POSSESSIVE.sub("", t)
    t = t.replace("'", "")
    t = _NON_TOKEN_CHARS.sub(" ", t)
    t = _EDGE_JOINERS.sub(" ", t)
    return " ".join(t.split())


def tokenize(text: str) -> list[str]:
    """Lowercased word tokens (of normalized text), including identifiers like p99."""
    return [m.group(0) for m in TOKEN_RE.finditer(normalize_text(text))]


def is_identifier(token: str) -> bool:
    """Identifier-like tokens (p99, checkout-api, checkout_retry, 2410) match exactly.

    Typo and synonym tolerance never rewrite these: users copy-paste them.
    """
    return any(ch.isdigit() or ch in _IDENTIFIER_CHARS for ch in token)


def content_tokens(text: str) -> list[str]:
    """Tokens with stopwords, politeness filler, and 1-char noise removed."""
    out: list[str] = []
    for tok in tokenize(text):
        if tok in NON_SALIENT:
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
