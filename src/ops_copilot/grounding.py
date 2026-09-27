"""Lexical grounding: IDF-weighted coverage plus a high-IDF key-token gate.

Salience policy (which query words evidence must support):

- stopwords and politeness/discourse filler (``text.NON_SALIENT``) are never
  salient, so "Hey team, sorry to bother you" cannot outweigh the question;
- identifiers and numbers (``text.is_identifier``) are salient and exact-only;
- corpus-known content words are salient with their corpus IDF;
- any other unknown word stays salient with the high OOV weight. That is
  deliberate: "millicore", "chargeback", or "SAP" are unknown *content*, and
  counting them as missing is what keeps the ungrounded / no-evidence traps
  refusing. Only filler is exempt, never unfamiliar content.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from ops_copilot.text import content_tokens, idf_map, is_identifier, match_tokens
from ops_copilot.types import Chunk, GroundingResult


@dataclass(frozen=True)
class QueryTerm:
    """One salient query term and the evidence forms that count as support."""

    token: str
    kind: str  # identifier | known | unknown
    weight: float
    alts: frozenset[str]

    def supported_by(self, evidence_forms: set[str]) -> bool:
        return any(a in evidence_forms for a in self.alts)


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

    def _term(self, tok: str) -> QueryTerm:
        if is_identifier(tok):
            kind = "identifier"
        elif tok in self.idf:
            kind = "known"
        else:
            kind = "unknown"
        return QueryTerm(token=tok, kind=kind, weight=self._weight(tok), alts=frozenset({tok}))

    def terms(self, query: str) -> list[QueryTerm]:
        """Unique salient terms of ``query`` in first-seen order."""
        seen: set[str] = set()
        out: list[QueryTerm] = []
        for tok in content_tokens(query):
            if tok in seen:
                continue
            seen.add(tok)
            out.append(self._term(tok))
        return out

    def _unique(self, text: str) -> list[str]:
        return [t.token for t in self.terms(text)]

    def _key_terms(self, terms: list[QueryTerm], k: int | None = None) -> list[QueryTerm]:
        ranked = sorted(terms, key=lambda t: t.weight, reverse=True)
        if k is None:
            k = max(1, math.ceil(len(ranked) / 2.0))
        return ranked[: min(k, len(ranked))]

    def key_tokens(self, query: str, k: int | None = None) -> list[str]:
        return [t.token for t in self._key_terms(self.terms(query), k)]

    def keys_supported(self, query: str, evidence: str) -> bool:
        """Every term in the high-IDF half of the query must appear in evidence."""
        keys = self._key_terms(self.terms(query))
        if not keys:
            return False
        ev = match_tokens(content_tokens(evidence))
        return all(t.supported_by(ev) for t in keys)

    def missing_key_tokens(self, query: str, evidence: str) -> list[str]:
        """High-IDF query terms the evidence does not support (for traces)."""
        ev = match_tokens(content_tokens(evidence))
        return [t.token for t in self._key_terms(self.terms(query)) if not t.supported_by(ev)]

    def coverage(self, query: str, evidence: str) -> tuple[float, list[str]]:
        terms = self.terms(query)
        if not terms:
            return 0.0, []
        ev = match_tokens(content_tokens(evidence))
        hit = [t for t in terms if t.supported_by(ev)]
        present = sum(t.weight for t in hit)
        total = sum(t.weight for t in terms)
        overlap = [t.token for t in hit]
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
