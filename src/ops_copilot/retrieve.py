"""BM25 baseline plus an embedding-free dense stub (title char-hash cosine).

``Retriever.search`` keeps the hybrid BM25 + body TF-IDF path used for
answer evidence. Disagreement routing compares ``search_bm25`` against
``search_dense_stub`` (``TitleHashDenseStub``) — an offline stand-in for a
real dense embedder that often ranks title-similar decoys differently from
full-text BM25.

Every ranker sees the query through ``text.normalize_text`` (and corpus text
through the same function), so a '?' stuck to the last word or a curly quote
cannot change BM25 terms, TF-IDF terms, or the dense stub's char n-grams.

``Retriever.rewrite_query`` additionally drops politeness filler and replaces
unknown plain words with their unique one-edit corpus neighbour ("checkuot"
-> "checkout") or, failing that, with the corpus-known members of their
``synonyms.OPS_EQUIVALENTS`` group ("instances" -> "replicas"), or, when the
optional semantic backoff is on and nothing else matched, with its closest
corpus words (``semantic.SemanticBackoff``). Known corpus words and
identifiers are never rewritten.
"""

from __future__ import annotations

import math
from collections import Counter
from dataclasses import replace

import numpy as np
from sklearn.feature_extraction.text import HashingVectorizer, TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from ops_copilot.config import CopilotConfig
from ops_copilot.lexicon import CorpusVocabulary, fix_interrogative_typos
from ops_copilot.semantic import SemanticBackoff
from ops_copilot.synonyms import equivalents, fold_phrases
from ops_copilot.text import (
    FILLER_WORDS,
    NON_SALIENT,
    content_tokens,
    is_identifier,
    normalize_text,
    tokenize,
)
from ops_copilot.types import Chunk

try:
    from rank_bm25 import BM25Okapi
except ImportError:  # pragma: no cover - fallback for air-gapped CI
    BM25Okapi = None  # type: ignore[misc, assignment]


class _OkapiBM25:
    """Minimal Okapi BM25 used when rank_bm25 is not installed."""

    def __init__(self, corpus: list[list[str]], k1: float = 1.5, b: float = 0.75) -> None:
        self.k1 = k1
        self.b = b
        self.corpus = corpus
        self.n = len(corpus)
        self.doc_len = [len(doc) for doc in corpus]
        self.avgdl = (sum(self.doc_len) / self.n) if self.n else 0.0
        df: Counter[str] = Counter()
        for doc in corpus:
            df.update(set(doc))
        self.idf = {
            term: math.log((self.n - count + 0.5) / (count + 0.5) + 1.0)
            for term, count in df.items()
        }
        self.tfs = [Counter(doc) for doc in corpus]

    def get_scores(self, query: list[str]) -> np.ndarray:
        scores = np.zeros(self.n, dtype=float)
        if self.avgdl <= 0:
            return scores
        for i, tf in enumerate(self.tfs):
            acc = 0.0
            dl = self.doc_len[i]
            denom_scale = self.k1 * (1.0 - self.b + self.b * dl / self.avgdl)
            for term in query:
                freq = tf.get(term, 0)
                if not freq:
                    continue
                idf = self.idf.get(term, 0.0)
                acc += idf * (freq * (self.k1 + 1.0)) / (freq + denom_scale)
            scores[i] = acc
        return scores


def _bm25_engine(tokenized: list[list[str]]):
    if BM25Okapi is not None:
        return BM25Okapi(tokenized)
    return _OkapiBM25(tokenized)


class TitleHashDenseStub:
    """Offline dense stub: char n-gram hashing cosine over document *titles*.

    Named explicitly so reviewers do not confuse it with a paid embedding API.
    Hyphenated title decoys that BM25 tokenizes as a single term still match
    spaced queries via character n-grams — a reproducible disagreement source.
    """

    name = "title_hash_dense_stub"

    def __init__(
        self,
        chunks: list[Chunk],
        *,
        n_features: int = 2048,
        ngram_range: tuple[int, int] = (3, 5),
    ) -> None:
        if not chunks:
            raise ValueError("dense stub requires at least one chunk")
        self.chunks = chunks
        self._vectorizer = HashingVectorizer(
            analyzer="char_wb",
            ngram_range=ngram_range,
            n_features=n_features,
            alternate_sign=False,
            norm="l2",
            preprocessor=normalize_text,
        )
        self._matrix = self._vectorizer.transform([c.title for c in chunks])

    def search(self, query: str, *, top_k: int = 5) -> list[Chunk]:
        dense = cosine_similarity(self._vectorizer.transform([query]), self._matrix).ravel()
        hits: list[Chunk] = []
        for idx in np.argsort(-dense):
            cos = float(dense[idx])
            if cos <= 0.0:
                continue
            hits.append(
                replace(
                    self.chunks[idx],
                    score=cos,
                    bm25=0.0,
                    dense=cos,
                )
            )
            if len(hits) >= top_k:
                break
        return hits


class Retriever:
    """Rank chunks with BM25, optional body TF-IDF hybrid, and a title dense stub."""

    def __init__(
        self,
        chunks: list[Chunk],
        config: CopilotConfig | None = None,
        *,
        semantic: SemanticBackoff | None = None,
    ) -> None:
        if not chunks:
            raise ValueError("retriever requires at least one chunk")
        self.chunks = chunks
        self.config = config or CopilotConfig()
        self.semantic = semantic
        self._tokenized = [tokenize(f"{c.title} {c.text}") for c in chunks]
        self._bm25 = _bm25_engine(self._tokenized)
        self.vocab = CorpusVocabulary(self._tokenized, extra_words=NON_SALIENT)
        self._vectorizer: TfidfVectorizer | None = None
        self._matrix = None
        if self.config.use_dense:
            self._vectorizer = TfidfVectorizer(
                preprocessor=normalize_text,
                token_pattern=r"[a-z0-9][a-z0-9_\-]{1,}",
            )
            corpus_text = [f"{c.title} {c.text}" for c in chunks]
            self._matrix = self._vectorizer.fit_transform(corpus_text)
        self.dense_stub = TitleHashDenseStub(chunks)

    def rewrite_query(self, query: str) -> str:
        """Normalized query: filler dropped, typos and unknown synonyms snapped."""
        cfg = self.config
        text = normalize_text(query)
        if cfg.typo_tolerance:
            text = fix_interrogative_typos(text, self.vocab)
        if cfg.use_synonyms:
            text = fold_phrases(text)
        words: list[str] = []
        for word in text.split():
            if word in FILLER_WORDS:
                continue
            if not word.isalpha() or is_identifier(word) or word in self.vocab:
                words.append(word)
                continue
            if cfg.use_synonyms:
                known = sorted(w for w in equivalents(word) if w in self.vocab)
                if known:
                    words.extend(known)
                    continue
            if cfg.typo_tolerance:
                if self.vocab.is_typo_of_any(word, FILLER_WORDS):
                    continue
                fixed = self.vocab.correct(word)
                if fixed is not None:
                    words.append(fixed)
                    continue
            if self.semantic is not None:
                near = sorted(n.word for n in self.semantic.neighbours(word))
                if near:
                    words.extend(near)
                    continue
            words.append(word)
        return " ".join(words)

    def _bm25_scores(self, query: str) -> np.ndarray:
        return np.asarray(self._bm25.get_scores(tokenize(query)), dtype=float)

    def _body_tfidf_scores(self, query: str) -> np.ndarray:
        if self._vectorizer is None or self._matrix is None:
            return np.zeros(len(self.chunks), dtype=float)
        q_vec = self._vectorizer.transform([query])
        return cosine_similarity(q_vec, self._matrix).ravel()

    def _rank_from_scores(
        self,
        query: str,
        scores: np.ndarray,
        *,
        bm25_scores: np.ndarray | None = None,
        dense_scores: np.ndarray | None = None,
        top_k: int,
        apply_floors: bool,
    ) -> list[Chunk]:
        cfg = self.config
        bm25_scores = (
            np.asarray(bm25_scores, dtype=float)
            if bm25_scores is not None
            else np.zeros(len(self.chunks), dtype=float)
        )
        dense_scores = (
            np.asarray(dense_scores, dtype=float)
            if dense_scores is not None
            else np.zeros(len(self.chunks), dtype=float)
        )
        hits: list[Chunk] = []
        q_content = set(content_tokens(query))
        order = np.argsort(-scores)
        for idx in order:
            raw = float(bm25_scores[idx])
            cos = float(dense_scores[idx])
            combined = float(scores[idx])
            if apply_floors:
                overlap = q_content & set(
                    content_tokens(f"{self.chunks[idx].title} {self.chunks[idx].text}")
                )
                if raw < cfg.min_retrieve_score and cos < cfg.min_cosine:
                    continue
                if not overlap and raw < cfg.min_retrieve_score * 1.5:
                    continue
            elif combined <= 0.0 and raw <= 0.0 and cos <= 0.0:
                continue
            scored = replace(
                self.chunks[idx],
                score=combined,
                bm25=raw,
                dense=cos,
            )
            hits.append(scored)
            if len(hits) >= top_k:
                break
        return hits

    def search_bm25(self, query: str, *, top_k: int | None = None) -> list[Chunk]:
        """BM25-only ranking (full title+body text) for disagreement comparison."""
        k = top_k if top_k is not None else self.config.top_k
        bm25_scores = self._bm25_scores(query)
        return self._rank_from_scores(
            query,
            bm25_scores,
            bm25_scores=bm25_scores,
            top_k=k,
            apply_floors=False,
        )

    def search_dense_stub(self, query: str, *, top_k: int | None = None) -> list[Chunk]:
        """Title-hash dense stub ranking for disagreement comparison."""
        k = top_k if top_k is not None else self.config.top_k
        return self.dense_stub.search(query, top_k=k)

    def search(self, query: str, *, top_k: int | None = None) -> list[Chunk]:
        """Hybrid BM25 + body TF-IDF cosine used as the primary evidence path."""
        cfg = self.config
        k = top_k if top_k is not None else cfg.top_k
        bm25_scores = self._bm25_scores(query)
        dense = self._body_tfidf_scores(query)
        combined = bm25_scores + cfg.hybrid_dense_weight * dense * max(
            float(bm25_scores.max()), 1.0
        )
        return self._rank_from_scores(
            query,
            combined,
            bm25_scores=bm25_scores,
            dense_scores=dense,
            top_k=k,
            apply_floors=True,
        )
