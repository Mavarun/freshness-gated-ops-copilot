"""Lexical grounding: IDF-weighted coverage plus a high-IDF key-token gate."""

from __future__ import annotations

import math

from ops_copilot.text import content_tokens, idf_map, match_tokens
from ops_copilot.types import Chunk, GroundingResult


class Grounder:
    """Mark an answer ungrounded when the query is not supported by evidence."""

    def __init__(self, corpus_texts: list[str], threshold: float = 0.52) -> None:
        tokenized = [content_tokens(text) for text in corpus_texts]
        self.idf = idf_map(tokenized)
        self.n_docs = max(len(tokenized), 1)
        self.oov_idf = math.log(self.n_docs + 1.0) + 1.0
        self.threshold = threshold

    def _weight(self, token: str) -> float:
        return self.idf.get(token, self.oov_idf)

    def _unique(self, text: str) -> list[str]:
        seen: set[str] = set()
        uniq: list[str] = []
        for tok in content_tokens(text):
            if tok not in seen:
                seen.add(tok)
                uniq.append(tok)
        return uniq

    def key_tokens(self, query: str, k: int | None = None) -> list[str]:
        uniq = self._unique(query)
        ranked = sorted(uniq, key=self._weight, reverse=True)
        if k is None:
            k = max(1, math.ceil(len(ranked) / 2.0))
        return ranked[: min(k, len(ranked))]

    def keys_supported(self, query: str, evidence: str) -> bool:
        """Every token in the high-IDF half of the query must appear in evidence."""
        keys = self.key_tokens(query)
        if not keys:
            return False
        ev = match_tokens(content_tokens(evidence))
        return all(tok in ev for tok in keys)

    def coverage(self, query: str, evidence: str) -> tuple[float, list[str]]:
        uniq = self._unique(query)
        if not uniq:
            return 0.0, []
        ev = match_tokens(content_tokens(evidence))
        overlap = [t for t in uniq if t in ev]
        present = sum(self._weight(t) for t in overlap)
        total = sum(self._weight(t) for t in uniq)
        if total <= 0:
            return 0.0, overlap
        return present / total, overlap

    def support_score(self, query: str, evidence: str) -> float:
        """Coverage, zeroed when the key-token gate fails."""
        cov, _ = self.coverage(query, evidence)
        if not self.keys_supported(query, evidence):
            return 0.0
        return cov

    def check(
        self,
        query: str,
        evidence_chunks: list[Chunk],
        answer: str | None,
        threshold: float | None = None,
    ) -> GroundingResult:
        thresh = self.threshold if threshold is None else threshold
        evidence = " ".join(f"{c.title} {c.text}" for c in evidence_chunks)
        q_cov, overlap = self.coverage(query, evidence)
        keys_ok = self.keys_supported(query, evidence) if evidence_chunks else False
        if answer:
            a_cov, _ = self.coverage(answer, evidence)
        else:
            a_cov = 0.0
        answer_ok = (not answer) or a_cov >= 0.50
        passed = (
            q_cov >= thresh
            and keys_ok
            and bool(evidence_chunks)
            and answer_ok
            and bool(answer)
        )
        return GroundingResult(
            passed=passed,
            query_coverage=q_cov,
            answer_coverage=a_cov,
            threshold=thresh,
            overlap_tokens=overlap,
        )
