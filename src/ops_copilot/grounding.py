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
corpus-side equivalence group (``synonyms.OPS_EQUIVALENTS``; "usage" is
supported by "utilization"), and hyphen spellings are interchangeable ("oncall" ~
"on-call"). An unknown word whose group has a corpus-known member is weighted
like that member instead of as OOV. The eval's own perturbation map is never
consulted (see synonyms.py for the leakage note).

Tag-synonym backoff (optional, ``tag_synonyms.TagSynonymBackoff``): a word that
is still unknown after the synonym and typo steps may be supported by corpus
words that a Stack Exchange site's community made a tag synonym of it (an
external ops-domain resource), weighted like the heaviest of them. With
``tagsyn_known`` a known word's tag substitutes are also accepted as support.
It runs before the word-vector backoff.

Word-vector backoff (optional, ``word_vectors.WordVectorBackoff``): a word that
is still unknown after the synonym and typo steps may be supported by its
counter-fitted substitutes among the corpus words (an external PPDB/WordNet-
constrained resource, cosine >= a dev-calibrated threshold), weighted like the
heaviest of them. With ``wordvec_known`` a known word's substitutes are also
accepted as support. It runs before the corpus PPMI backoff.

Semantic backoff (optional, ``semantic.SemanticBackoff``): a word that is still
unknown after the synonym and typo steps may be supported by its closest
corpus words from the corpus PPMI/SVD embedding (or one char-trigram
neighbour), weighted like the heaviest of them. It is the last step, so it never
changes known words, identifiers, synonyms, or typo snaps.

Semantic grounding (optional, ``EmbeddingSupport``, sentence embeddings): a
salient term that is still *unknown* after all of the above (not a corpus word,
not an identifier or number, alphabetic) may count as supported by a chunk when
some sentence of that chunk has cosine >= ``threshold`` with the rewritten
query. The threshold is calibrated on the clean golden set plus the *dev*
synonym rows only (``scripts/calibrate_semantic_grounding.py``). It is a
backoff alongside the lexical checks, not a replacement: at most
``max_rescued_terms`` unknown words can be rescued per query, the answer
coverage check stays lexical, and in strict mode (default) the rescue only
applies when *every other* salient term of the query is matched lexically by
that evidence, and only for wh-questions. Strict mode exists because the
non-strict version answered the ``g19-synonym`` trap (*rollback steps*): the
flag page is topically close to the query, so ``steps`` was rescued while the
known word ``rollback`` was simply absent. The wh-question rule keeps an
unrecognised command (*Can you reboot payments-worker?*) off the read path.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Callable, Sequence

import numpy as np

from ops_copilot.embeddings import EmbeddingBackend, evidence_sentences

from ops_copilot.lexicon import WH_WORDS, CorpusVocabulary, fix_interrogative_typos
from ops_copilot.semantic import SemanticBackoff
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
from ops_copilot.tag_synonyms import TagSynonymBackoff
from ops_copilot.word_vectors import WordVectorBackoff


@dataclass(frozen=True)
class QueryTerm:
    """One salient query term and the evidence forms that count as support."""

    token: str
    kind: str  # identifier | known | typo | synonym | wordvec | semantic | unknown
    weight: float
    alts: frozenset[str]

    def supported_by(self, evidence_forms: set[str]) -> bool:
        return any(a in evidence_forms for a in self.alts)


class EmbeddingSupport:
    """Max cosine between the (rewritten) query and any evidence sentence."""

    def __init__(
        self,
        backend: EmbeddingBackend,
        threshold: float,
        *,
        query_form: Callable[[str], str] | None = None,
        max_rescued_terms: int = 1,
        strict: bool = True,
    ) -> None:
        self.backend = backend
        self.strict = bool(strict)
        self.threshold = float(threshold)
        self.query_form = query_form or normalize_text
        self.max_rescued_terms = int(max_rescued_terms)
        self._qcache: dict[str, np.ndarray | None] = {}

    def query_vector(self, query: str) -> np.ndarray | None:
        if query not in self._qcache:
            self._qcache[query] = self.backend.vector(self.query_form(query))
        return self._qcache[query]

    def best_similarity(self, query: str, evidence_parts: Sequence[str]) -> float | None:
        """Highest query-sentence cosine, or ``None`` when nothing is embeddable."""
        qv = self.query_vector(query)
        if qv is None:
            return None
        sentences = [s for part in evidence_parts for s in evidence_sentences(part)]
        vecs = [v for v in self.backend.lookup(sentences) if v is not None]
        if not vecs:
            return None
        return float(np.max(np.vstack(vecs) @ qv))

    def supports(self, query: str, evidence_parts: Sequence[str]) -> bool:
        best = self.best_similarity(query, evidence_parts)
        return best is not None and best >= self.threshold


@dataclass(frozen=True)
class Support:
    """Which salient terms an evidence text supports, lexically or semantically."""

    terms: list[QueryTerm]
    lexical: frozenset[str]
    rescued: frozenset[str]
    similarity: float | None

    def ok(self, term: QueryTerm) -> bool:
        return term.token in self.lexical or term.token in self.rescued


class Grounder:
    """Mark an answer ungrounded when the query is not supported by evidence."""

    def __init__(
        self,
        corpus_texts: list[str],
        threshold: float = 0.52,
        *,
        typo_tolerance: bool = True,
        synonyms: bool = True,
        semantic: SemanticBackoff | None = None,
        embed_support: EmbeddingSupport | None = None,
        wordvec: WordVectorBackoff | None = None,
        wordvec_known: bool = False,
        tagsyn: TagSynonymBackoff | None = None,
        tagsyn_known: bool = False,
    ) -> None:
        tokenized = [content_tokens(text) for text in corpus_texts]
        self.idf = idf_map(tokenized)
        self.n_docs = max(len(tokenized), 1)
        self.oov_idf = math.log(self.n_docs + 1.0) + 1.0
        self.threshold = threshold
        self.typo_tolerance = typo_tolerance
        self.synonyms = synonyms
        self.semantic = semantic
        self.embed_support = embed_support
        self.wordvec = wordvec
        self.wordvec_known = bool(wordvec_known and wordvec is not None)
        self.tagsyn = tagsyn
        self.tagsyn_known = bool(tagsyn_known and tagsyn is not None)
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
            alts = self._alts(tok)
            if self.tagsyn_known:
                alts = alts | self._tagsyn_near(tok)
            if self.wordvec_known:
                alts = alts | self._wordvec_near(tok)
            return QueryTerm(tok, "known", self._weight(tok), alts)
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
        if self.tagsyn is not None and not is_identifier(tok):
            ts = self._tagsyn_near(tok)
            if ts:
                weight = max(self._weight(w) for w in ts)
                return QueryTerm(tok, "tagsyn", weight, frozenset({tok, *ts}))
        if self.wordvec is not None and not is_identifier(tok):
            wv = self._wordvec_near(tok)
            if wv:
                weight = max(self._weight(w) for w in wv)
                return QueryTerm(tok, "wordvec", weight, frozenset({tok, *wv}))
        if self.semantic is not None and not is_identifier(tok):
            near = [n.word for n in self.semantic.neighbours(tok) if n.word in self.idf]
            if near:
                weight = max(self._weight(w) for w in near)
                return QueryTerm(tok, "semantic", weight, frozenset({tok, *near}))
        return QueryTerm(tok, "unknown", self.oov_idf, frozenset({tok}))

    def _tagsyn_near(self, tok: str) -> frozenset[str]:
        """Tag-synonym substitutes of ``tok`` that are corpus words."""
        if self.tagsyn is None:
            return frozenset()
        return frozenset(n.word for n in self.tagsyn.neighbours(tok) if n.word in self.idf)

    def _wordvec_near(self, tok: str) -> frozenset[str]:
        """Counter-fitted substitutes of ``tok`` that are corpus words."""
        if self.wordvec is None:
            return frozenset()
        return frozenset(n.word for n in self.wordvec.neighbours(tok) if n.word in self.idf)

    def _query_tokens(self, query: str) -> list[str]:
        text = normalize_text(query)
        if self.typo_tolerance:
            text = fix_interrogative_typos(text, self.vocab)
        if self.synonyms:
            text = fold_phrases(text)
        return content_tokens(text)

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

    def is_wh_question(self, query: str) -> bool:
        text = normalize_text(query)
        if self.typo_tolerance:
            text = fix_interrogative_typos(text, self.vocab)
        return any(w in WH_WORDS for w in text.split())

    @staticmethod
    def rescuable(term: QueryTerm) -> bool:
        """Only still-unknown plain words may be supported by embeddings."""
        return term.kind == "unknown" and term.token.isalpha() and not is_identifier(term.token)

    def support(
        self,
        query: str,
        evidence: str,
        *,
        evidence_parts: Sequence[str] | None = None,
        semantic: bool = True,
    ) -> Support:
        """Lexical support per term, plus the semantic rescue when enabled."""
        terms = self.terms(query)
        ev = self._evidence_forms(evidence)
        lexical = frozenset(t.token for t in terms if t.supported_by(ev))
        rescued: frozenset[str] = frozenset()
        sim: float | None = None
        es = self.embed_support if semantic else None
        if es is not None and terms:
            missing = [t for t in terms if t.token not in lexical]
            candidates = [t for t in missing if self.rescuable(t)]
            # Strict mode: every other salient term must be matched lexically,
            # so a topical sentence cannot paper over a missing known word.
            complete = len(candidates) == len(missing) or not es.strict
            # Strict mode: only wh-questions (what / how / who ...) get a
            # semantic rescue. "Can you reboot X?" names an action the write
            # gate did not recognise; it must never become a read-path answer.
            question = not es.strict or self.is_wh_question(query)
            if candidates and complete and question and len(candidates) <= es.max_rescued_terms:
                sim = es.best_similarity(query, evidence_parts or [evidence])
                if sim is not None and sim >= es.threshold:
                    rescued = frozenset(t.token for t in candidates)
        return Support(terms, lexical, rescued, sim)

    def keys_supported(
        self, query: str, evidence: str, *, evidence_parts: Sequence[str] | None = None
    ) -> bool:
        """Every term in the high-IDF half of the query must appear in evidence."""
        sup = self.support(query, evidence, evidence_parts=evidence_parts)
        keys = self._key_terms(sup.terms)
        if not keys:
            return False
        return all(sup.ok(t) for t in keys)

    def missing_key_tokens(self, query: str, evidence: str) -> list[str]:
        """High-IDF query terms the evidence does not support (for traces)."""
        sup = self.support(query, evidence)
        return [t.token for t in self._key_terms(sup.terms) if not sup.ok(t)]

    def missing_terms(
        self, query: str, evidence: str, *, evidence_parts: Sequence[str] | None = None, k: int = 6
    ) -> list[str]:
        """Salient query terms ``evidence`` does not support, for refusal explanations.

        The high-IDF key terms come first (they are what the key-token gate
        checks), then the rest, each group by weight; at most ``k``.
        """
        sup = self.support(query, evidence, evidence_parts=evidence_parts)
        keys = self._key_terms(sup.terms)
        key_ids = {t.token for t in keys}
        rest = sorted((t for t in sup.terms if t.token not in key_ids), key=lambda t: t.weight, reverse=True)
        return [t.token for t in [*keys, *rest] if not sup.ok(t)][:k]

    def coverage(
        self, query: str, evidence: str, *, evidence_parts: Sequence[str] | None = None
    ) -> tuple[float, list[str]]:
        sup = self.support(query, evidence, evidence_parts=evidence_parts)
        return self._coverage(sup)

    @staticmethod
    def _coverage(sup: Support) -> tuple[float, list[str]]:
        if not sup.terms:
            return 0.0, []
        hit = [t for t in sup.terms if sup.ok(t)]
        present = sum(t.weight for t in hit)
        total = sum(t.weight for t in sup.terms)
        overlap = [t.token for t in hit]
        if total <= 0:
            return 0.0, overlap
        return present / total, overlap

    def chunk_support(self, query: str, evidence: str) -> tuple[float, bool]:
        """(coverage, key gate) for one chunk's evidence string, one pass."""
        sup = self.support(query, evidence)
        keys = self._key_terms(sup.terms)
        keys_ok = bool(keys) and all(sup.ok(t) for t in keys)
        return self._coverage(sup)[0], keys_ok

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
        parts = [f"{c.title} {c.text}" for c in evidence_chunks]
        evidence = " ".join(parts)
        sup = self.support(query, evidence, evidence_parts=parts)
        q_cov, overlap = self._coverage(sup)
        keys = self._key_terms(sup.terms)
        keys_ok = bool(evidence_chunks) and bool(keys) and all(sup.ok(t) for t in keys)
        if answer:
            # The draft is extracted from the evidence: lexical coverage only.
            a_cov, _ = self._coverage(self.support(answer, evidence, semantic=False))
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
            semantic_rescued=sorted(sup.rescued),
            semantic_similarity=sup.similarity,
        )
