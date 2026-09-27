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

Typo tolerance: an unknown, non-identifier word that is one edit away from a
unique corpus word (``lexicon.CorpusVocabulary.correct``) is matched as that
word ("checkuot" -> "checkout"); if it is one edit from a stopword/filler
("whhat", "crrent") it is dropped as filler. Identifiers stay exact-only.

Synonym awareness: a query word is also supported by any member of its
corpus-side equivalence group (``synonyms.OPS_EQUIVALENTS``; "health" is
supported by "status"), and hyphen spellings are interchangeable ("oncall" ~
"on-call"). An unknown word whose group has a corpus-known member is weighted
like that member instead of as OOV. The eval's own perturbation map is never
consulted (see synonyms.py for the leakage note).
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from ops_copilot.lexicon import CorpusVocabulary
from ops_copilot.synonyms import equivalents, fold_phrases, hyphen_variants
from ops_copilot.text import (
    NON_SALIENT,
    content_tokens,
    idf_map,
    is_identifier,
    match_tokens,
    normalize_text,
)
from ops_copilot.types import Chunk, GroundingResult


@dataclass(frozen=True)
class QueryTerm:
    """One salient query term and the evidence forms that count as support."""

    token: str
    kind: str  # identifier | known | typo | synonym | unknown
    weight: float
    alts: frozenset[str]

    def supported_by(self, evidence_forms: set[str]) -> bool:
        return any(a in evidence_forms for a in self.alts)


class Grounder:
    """Mark an answer ungrounded when the query is not supported by evidence."""

    def __init__(
        self,
        corpus_texts: list[str],
        threshold: float = 0.52,
        *,
        typo_tolerance: bool = True,
        synonyms: bool = True,
    ) -> None:
        tokenized = [content_tokens(text) for text in corpus_texts]
        self.idf = idf_map(tokenized)
        self.n_docs = max(len(tokenized), 1)
        self.oov_idf = math.log(self.n_docs + 1.0) + 1.0
        self.threshold = threshold
        self.typo_tolerance = typo_tolerance
        self.synonyms = synonyms
        self.vocab = CorpusVocabulary(tokenized, extra_words=NON_SALIENT)

    def _weight(self, token: str) -> float:
        return self.idf.get(token, self.oov_idf)

    def _alts(self, tok: str) -> frozenset[str]:
        alts = {tok}
        if self.synonyms:
            alts |= hyphen_variants(tok)
            if not is_identifier(tok):
                alts |= equivalents(tok)
        return frozenset(alts)

    def _term(self, tok: str) -> QueryTerm | None:
        """Classify one content token; ``None`` means non-salient (typo'd filler)."""
        if is_identifier(tok):
            return QueryTerm(tok, "identifier", self._weight(tok), self._alts(tok))
        if tok in self.idf:
            return QueryTerm(tok, "known", self._weight(tok), self._alts(tok))
        if self.synonyms:
            known = [w for w in equivalents(tok) if w in self.idf]
            if known:
                weight = max(self._weight(w) for w in known)
                return QueryTerm(tok, "synonym", weight, self._alts(tok))
        if self.typo_tolerance:
            fixed = self.vocab.correct(tok)
            if self.vocab.is_typo_of_any(tok, NON_SALIENT):
                return None
            if fixed is not None and fixed in self.idf:
                return QueryTerm(fixed, "typo", self._weight(fixed), self._alts(fixed))
        return QueryTerm(tok, "unknown", self.oov_idf, frozenset({tok}))

    def _query_tokens(self, query: str) -> list[str]:
        if self.synonyms:
            return content_tokens(fold_phrases(normalize_text(query)))
        return content_tokens(query)

    def _evidence_forms(self, evidence: str) -> set[str]:
        forms = match_tokens(content_tokens(evidence))
        if self.synonyms:
            forms |= {v for tok in list(forms) for v in hyphen_variants(tok)}
        return forms

    def terms(self, query: str) -> list[QueryTerm]:
        """Unique salient terms of ``query`` in first-seen order."""
        seen: set[str] = set()
        out: list[QueryTerm] = []
        for tok in self._query_tokens(query):
            term = self._term(tok)
            if term is None or term.token in seen:
                continue
            seen.add(term.token)
            out.append(term)
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
        ev = self._evidence_forms(evidence)
        return all(t.supported_by(ev) for t in keys)

    def missing_key_tokens(self, query: str, evidence: str) -> list[str]:
        """High-IDF query terms the evidence does not support (for traces)."""
        ev = self._evidence_forms(evidence)
        return [t.token for t in self._key_terms(self.terms(query)) if not t.supported_by(ev)]

    def coverage(self, query: str, evidence: str) -> tuple[float, list[str]]:
        terms = self.terms(query)
        if not terms:
            return 0.0, []
        ev = self._evidence_forms(evidence)
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
