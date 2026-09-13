"""BM25 baseline plus an embedding-free TF-IDF cosine dense stub."""

from __future__ import annotations

import math
from collections import Counter
from dataclasses import replace

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from ops_copilot.config import CopilotConfig
from ops_copilot.text import content_tokens, tokenize
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


class Retriever:
    """Rank chunks with BM25 and optional TF-IDF cosine; return metadata-rich hits."""

    def __init__(self, chunks: list[Chunk], config: CopilotConfig | None = None) -> None:
        if not chunks:
            raise ValueError("retriever requires at least one chunk")
        self.chunks = chunks
        self.config = config or CopilotConfig()
        self._tokenized = [tokenize(f"{c.title} {c.text}") for c in chunks]
        self._bm25 = _bm25_engine(self._tokenized)
        self._vectorizer: TfidfVectorizer | None = None
        self._matrix = None
        if self.config.use_dense:
            self._vectorizer = TfidfVectorizer(
                lowercase=True,
                token_pattern=r"[a-z0-9][a-z0-9_\-]{1,}",
            )
            corpus_text = [f"{c.title} {c.text}" for c in chunks]
            self._matrix = self._vectorizer.fit_transform(corpus_text)

    def search(self, query: str, *, top_k: int | None = None) -> list[Chunk]:
        cfg = self.config
        k = top_k if top_k is not None else cfg.top_k
        q_tokens = tokenize(query)
        bm25_scores = np.asarray(self._bm25.get_scores(q_tokens), dtype=float)
        dense = np.zeros(len(self.chunks), dtype=float)
        if self._vectorizer is not None and self._matrix is not None:
            q_vec = self._vectorizer.transform([query])
            dense = cosine_similarity(q_vec, self._matrix).ravel()

        combined = bm25_scores + cfg.hybrid_dense_weight * dense * max(float(bm25_scores.max()), 1.0)

        hits: list[Chunk] = []
        q_content = set(content_tokens(query))
        order = np.argsort(-combined)
        for idx in order:
            raw = float(bm25_scores[idx])
            cos = float(dense[idx])
            overlap = q_content & set(content_tokens(f"{self.chunks[idx].title} {self.chunks[idx].text}"))
            if raw < cfg.min_retrieve_score and cos < cfg.min_cosine:
                continue
            if not overlap and raw < cfg.min_retrieve_score * 1.5:
                continue
            scored = replace(
                self.chunks[idx],
                score=float(combined[idx]),
                bm25=raw,
                dense=cos,
            )
            hits.append(scored)
            if len(hits) >= k:
                break
        return hits
