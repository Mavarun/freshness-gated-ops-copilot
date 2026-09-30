"""Offline semantic backoff: a corpus PPMI/SVD word embedding + char n-grams.

Small, deterministic, and dependency-light (numpy only; no downloads, no API).
It is the last resort for a query word that grounding and retrieval could not
place any other way: not a corpus word, not an identifier, not in the
corpus-side synonym map, and not a keyboard slip of a corpus word.

Two similarity sources:

- ``PpmiSvdEmbedding``: symmetric-window co-occurrence counts (1/distance
  weighting, window 4) over sentences of the corpus docs plus the generic
  glossary in ``data/glossary/ops_glossary.txt``; positive PMI with context
  smoothing (alpha 0.75); a full numpy SVD truncated to ``dim`` columns scaled
  by sqrt(singular value); rows L2-normalised; each column's sign fixed so its
  largest-magnitude entry is positive (bit-for-bit stable across runs).
  Identifiers (digits, ``-_.``) and stopwords/filler are excluded.
- ``char_similarity``: Dice overlap of padded character trigrams, used only
  when the unknown word is not in the embedding vocabulary at all.

Only glossary lines can put a non-corpus word into the embedding, and the
glossary may not contain a held-out eval word, so on held-out rows the
embedding can only ever help through words the corpus itself uses.

``SemanticBackoff.neighbours`` returns at most ``max_neighbours`` corpus words
whose embedding cosine clears ``min_similarity``; the char-trigram fallback
returns a single word and only when it also beats the runner-up by a margin
(spelling neighbours are ambiguous far more often than they are right).
Returning nothing is always the safe answer: the word then stays an unknown,
high-weight term and grounding refuses as before. The backoff never touches
known corpus words, identifiers, or the write gate, so it cannot turn a read
into PROPOSE_WRITE, and it never adds evidence, only a way for existing
evidence to count.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from ops_copilot.text import content_tokens, fold_token, is_identifier, split_sentences

DEFAULT_GLOSSARY = (
    Path(__file__).resolve().parents[2] / "data" / "glossary" / "ops_glossary.txt"
)
MIN_WORD_LEN = 4


def load_glossary(path: str | Path | None = None) -> list[str]:
    """Non-comment, non-empty glossary lines."""
    src = Path(path) if path else DEFAULT_GLOSSARY
    if not src.is_file():
        return []
    lines = src.read_text(encoding="utf-8").splitlines()
    return [ln.strip() for ln in lines if ln.strip() and not ln.lstrip().startswith("#")]


def _plain(tok: str) -> bool:
    return tok.isalpha() and not is_identifier(tok)


def sentence_tokens(texts: Iterable[str]) -> list[list[str]]:
    """Folded, non-identifier content tokens per sentence."""
    out: list[list[str]] = []
    for text in texts:
        for sent in split_sentences(text):
            toks = [fold_token(t) for t in content_tokens(sent) if _plain(t)]
            if toks:
                out.append(toks)
    return out


class PpmiSvdEmbedding:
    """Positive-PMI co-occurrence matrix factorised with a truncated SVD."""

    def __init__(
        self,
        sentences: list[list[str]],
        *,
        window: int = 4,
        dim: int = 32,
        alpha: float = 0.75,
    ) -> None:
        counts = Counter(t for s in sentences for t in s)
        self.vocab: tuple[str, ...] = tuple(sorted(counts))
        self.index = {w: i for i, w in enumerate(self.vocab)}
        n = len(self.vocab)
        if n == 0:
            self.vectors = np.zeros((0, 0))
            return
        cooc = np.zeros((n, n), dtype=float)
        for sent in sentences:
            for i, a in enumerate(sent):
                lo, hi = max(0, i - window), min(len(sent), i + window + 1)
                for j in range(lo, hi):
                    if j != i:
                        cooc[self.index[a], self.index[sent[j]]] += 1.0 / abs(i - j)
        total = cooc.sum()
        if total <= 0:
            self.vectors = np.zeros((n, 0))
            return
        row = cooc.sum(axis=1, keepdims=True)
        ctx = cooc.sum(axis=0, keepdims=True) ** alpha
        ctx = ctx / ctx.sum() * total
        with np.errstate(divide="ignore", invalid="ignore"):
            pmi = np.log((cooc * total) / (row * ctx))
        ppmi = np.where(np.isfinite(pmi) & (pmi > 0.0), pmi, 0.0)
        u, s, _ = np.linalg.svd(ppmi, full_matrices=False)
        k = max(1, min(dim, len(s)))
        vecs = u[:, :k] * np.sqrt(s[:k])
        signs = np.sign(vecs[np.abs(vecs).argmax(axis=0), np.arange(k)])
        vecs = vecs * np.where(signs == 0, 1.0, signs)
        norms = np.linalg.norm(vecs, axis=1, keepdims=True)
        self.vectors = vecs / np.where(norms == 0, 1.0, norms)

    def __contains__(self, word: str) -> bool:
        return word in self.index

    def similarity(self, a: str, b: str) -> float:
        if a not in self.index or b not in self.index:
            return 0.0
        return float(self.vectors[self.index[a]] @ self.vectors[self.index[b]])

    def ranked(self, word: str, candidates: Iterable[str]) -> list[tuple[str, float]]:
        """Candidates in the vocabulary, most similar first (ties by spelling)."""
        if word not in self.index:
            return []
        v = self.vectors[self.index[word]]
        scored = [
            (c, float(v @ self.vectors[self.index[c]]))
            for c in candidates
            if c in self.index and c != word
        ]
        return sorted(scored, key=lambda cs: (-cs[1], cs[0]))


def char_ngrams(word: str, n: int = 3) -> frozenset[str]:
    padded = f"<{word}>"
    if len(padded) <= n:
        return frozenset({padded})
    return frozenset(padded[i : i + n] for i in range(len(padded) - n + 1))


def char_similarity(a: str, b: str, n: int = 3) -> float:
    """Dice coefficient of padded character n-gram sets."""
    ga, gb = char_ngrams(a, n), char_ngrams(b, n)
    if not ga or not gb:
        return 0.0
    return 2.0 * len(ga & gb) / (len(ga) + len(gb))


@dataclass(frozen=True)
class Neighbour:
    word: str
    similarity: float
    source: str  # embedding | char


class SemanticBackoff:
    """Map an unplaceable query word to a few corpus words (or none)."""

    def __init__(
        self,
        corpus_texts: list[str],
        *,
        glossary_lines: list[str] | None = None,
        dim: int = 32,
        window: int = 4,
        min_similarity: float = 0.60,
        max_neighbours: int = 1,
        min_margin: float = 0.05,
        use_char_ngrams: bool = True,
        char_min_similarity: float = 0.72,
    ) -> None:
        glossary = load_glossary() if glossary_lines is None else glossary_lines
        corpus_sents = sentence_tokens(corpus_texts)
        self.corpus_words: frozenset[str] = frozenset(
            t for s in corpus_sents for t in s if len(t) >= MIN_WORD_LEN
        )
        self.embedding = PpmiSvdEmbedding(
            corpus_sents + sentence_tokens(glossary), window=window, dim=dim
        )
        self.min_similarity = min_similarity
        self.max_neighbours = max_neighbours
        self.min_margin = min_margin
        self.use_char_ngrams = use_char_ngrams
        self.char_min_similarity = char_min_similarity
        self._cache: dict[str, tuple[Neighbour, ...]] = {}

    def _embedding_neighbours(self, tok: str) -> tuple[Neighbour, ...]:
        ranked = self.embedding.ranked(tok, self.corpus_words)
        return tuple(
            Neighbour(w, round(sim, 6), "embedding")
            for w, sim in ranked[: self.max_neighbours]
            if sim >= self.min_similarity
        )

    def _char_neighbour(self, tok: str) -> tuple[Neighbour, ...]:
        scored = sorted(
            ((w, char_similarity(tok, w)) for w in self.corpus_words),
            key=lambda cs: (-cs[1], cs[0]),
        )
        if not scored or scored[0][1] < self.char_min_similarity:
            return ()
        if len(scored) > 1 and scored[0][1] - scored[1][1] < self.min_margin:
            return ()  # ambiguous spelling neighbour: refuse to guess
        return (Neighbour(scored[0][0], round(scored[0][1], 6), "char"),)

    def neighbours(self, token: str) -> tuple[Neighbour, ...]:
        """Corpus words standing in for an unknown plain ``token`` (may be empty)."""
        tok = fold_token(token)
        if tok in self._cache:
            return self._cache[tok]
        found: tuple[Neighbour, ...] = ()
        if _plain(tok) and len(tok) >= MIN_WORD_LEN and tok not in self.corpus_words:
            if tok in self.embedding:
                found = self._embedding_neighbours(tok)
            elif self.use_char_ngrams:
                found = self._char_neighbour(tok)
        self._cache[tok] = found
        return found
