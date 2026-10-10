"""Compose retrieve → support → freshness → disagreement → extractive draft → policy.

HITL: imperative writes become PROPOSE_WRITE via HitlWriteLedger (pending until approve);
write-shaped instructions the parser cannot pin down become REFUSE_AMBIGUOUS_WRITE.

Session cost budget is checked first in policy when a session_id is provided:
spent + this request's approx_cost_units must stay within session_budget_cost_units.
"""

from __future__ import annotations

import time
from datetime import datetime
from pathlib import Path

from ops_copilot.answer import extractive_answer, render_refusal
from ops_copilot.canary import CanaryRegistry, scan_answer
from ops_copilot.pii_redact import scan_answer_pii
from ops_copilot.config import CopilotConfig, parse_clock
from ops_copilot.corpus import Corpus
from ops_copilot.cost_budget import SessionCostLedger
from ops_copilot.hitl import HitlWriteLedger
from ops_copilot.oncall_rotation import rotation_from_docs
from ops_copilot.disagreement import assess_disagreement
from ops_copilot.embeddings import resolve_backend
from ops_copilot.explain import ExplainContext, GroundingGap
from ops_copilot.explain_redact import redact_string
from ops_copilot.pii import detect_pii
from ops_copilot.freshness import annotate, fresh_only
from ops_copilot.grounding import EmbeddingSupport, Grounder
from ops_copilot.policy import decide
from ops_copilot.retrieve import Retriever
from ops_copilot.semantic import SemanticBackoff
from ops_copilot.passage_support import PassageSupportModel
from ops_copilot.qa_translation import AnswerSupportModel
from ops_copilot.tag_synonyms import TagSynonymBackoff, tag_synonym_sites
from ops_copilot.wiktionary_senses import WiktionarySenseBackoff
from ops_copilot.word_vectors import WordVectorBackoff
from ops_copilot.source_slas import SourceSlaTable, load_source_slas, resolve_max_age
from ops_copilot.types import Chunk, CopilotResult, Decision
from ops_copilot.write_actions import proposal_from_intent
from ops_copilot.write_intent import AMBIGUOUS, classify_write_intent
from ops_copilot.write_prototypes import PrototypeBackoff
from ops_copilot.write_targets import EntityRegistry, default_registry


def _cost_units(n_retrieved: int, use_dense: bool, use_disagreement: bool) -> float:
    # Synthetic accounting units — no paid LLM in this path.
    return (
        1.0
        + 0.15 * n_retrieved
        + (0.40 if use_dense else 0.0)
        + (0.25 if use_disagreement else 0.0)
    )


def supporting_chunks(
    query: str,
    chunks: list[Chunk],
    grounder: Grounder,
    threshold: float,
) -> tuple[list[Chunk], float]:
    """Keep chunks whose IDF-weighted query coverage clears ``threshold``."""
    kept: list[Chunk] = []
    best = 0.0
    for chunk in chunks:
        text = f"{chunk.title} {chunk.text}"
        cov, keys_ok = grounder.chunk_support(query, text)
        if cov > best:
            best = cov
        if cov >= threshold and keys_ok:
            kept.append(chunk)
    return kept, best


class Copilot:
    """Offline ops copilot with freshness, disagreement, and session budget gates."""

    def __init__(
        self,
        corpus: Corpus | None = None,
        config: CopilotConfig | None = None,
        *,
        path: str | Path | None = None,
        now: datetime | str | None = None,
        sla_table: SourceSlaTable | None = None,
        ledger: SessionCostLedger | None = None,
        hitl: HitlWriteLedger | None = None,
    ) -> None:
        self.config = config or CopilotConfig()
        self.corpus = corpus or Corpus(path=path, now=now)
        texts = [f"{c.title} {c.text}" for c in self.corpus.chunks]
        self.semantic = (
            SemanticBackoff(
                texts,
                min_similarity=self.config.semantic_min_similarity,
                max_neighbours=self.config.semantic_max_neighbours,
                use_char_ngrams=self.config.semantic_char_ngrams,
            )
            if self.config.use_semantic_backoff
            else None
        )
        self.wordvec = (
            WordVectorBackoff(
                texts,
                min_similarity=self.config.word_vector_min_similarity,
                max_neighbours=self.config.word_vector_max_neighbours,
            )
            if self.config.use_word_vector_backoff
            else None
        )
        self.tagsyn = (
            TagSynonymBackoff(
                texts,
                sites=tag_synonym_sites(self.config.tag_synonym_sites),
                min_sites=self.config.tag_synonym_min_sites,
                max_neighbours=self.config.tag_synonym_max_neighbours,
            )
            if self.config.use_tag_synonym_backoff
            else None
        )
        self.wiktionary = (
            WiktionarySenseBackoff(
                texts,
                min_score=self.config.wiktionary_min_score,
                max_neighbours=self.config.wiktionary_max_neighbours,
            )
            if self.config.use_wiktionary_backoff
            else None
        )
        self.answer_support = (
            AnswerSupportModel(
                texts,
                min_score=self.config.answer_support_min_score,
                # the table is bound to the default corpus; a custom corpus
                # simply gets no support for its new words
                check_corpus=path is None and corpus is None,
            )
            if self.config.use_answer_support_model
            else None
        )
        self.passage_support = (
            PassageSupportModel.load() if self.config.use_passage_support_model else None
        )
        self.embeddings = resolve_backend(
            self.config.embedding_backend,
            model_name=self.config.embedding_model,
            allow_download=self.config.embedding_allow_download,
        )
        self.retriever = Retriever(
            self.corpus.chunks,
            self.config,
            semantic=self.semantic,
            embeddings=self.embeddings,
            wordvec=self.wordvec,
            tagsyn=self.tagsyn,
            wiktionary=self.wiktionary,
        )
        self.grounder = Grounder(
            texts,
            threshold=self.config.grounding_threshold,
            typo_tolerance=self.config.typo_tolerance,
            synonyms=self.config.use_synonyms,
            semantic=self.semantic,
            wordvec=self.wordvec,
            wordvec_known=self.config.word_vector_known_words,
            tagsyn=self.tagsyn,
            tagsyn_known=self.config.tag_synonym_known_words,
            wiktionary=self.wiktionary,
            wiktionary_known=self.config.wiktionary_known_words,
            answer_support=self.answer_support,
            answer_known=self.config.answer_support_known_words,
            answer_max_terms=self.config.answer_support_max_terms,
            answer_strict=self.config.answer_support_strict,
            passage_support=self.passage_support,
            passage_min_prob=self.config.passage_support_min_prob,
            passage_known=self.config.passage_support_known_words,
            passage_max_terms=self.config.passage_support_max_terms,
            passage_strict=self.config.passage_support_strict,
            embed_support=(
                EmbeddingSupport(
                    self.embeddings,
                    self.config.semantic_grounding_threshold,
                    query_form=self.retriever.rewrite_query,
                    max_rescued_terms=self.config.semantic_grounding_max_terms,
                    strict=self.config.semantic_grounding_strict,
                )
                if self.embeddings is not None and self.config.embed_semantic_grounding
                else None
            ),
        )
        if sla_table is not None:
            self.sla_table = sla_table
        elif self.config.use_source_slas:
            self.sla_table = load_source_slas(self.config.source_sla_path)
        else:
            self.sla_table = None
        self.ledger = ledger if ledger is not None else SessionCostLedger()
        self.hitl = hitl if hitl is not None else HitlWriteLedger()
        self.canary_registry = CanaryRegistry.load(self.config.canary_registry_path)
        self.registry = (
            default_registry()
            if path is None and corpus is None
            else EntityRegistry.from_texts(texts)
        )
        self.write_prototypes = (
            PrototypeBackoff(
                self.embeddings,
                threshold=self.config.write_prototype_threshold,
                margin=self.config.write_prototype_margin,
            )
            if self.config.write_prototype_backoff and self.embeddings is not None
            else None
        )
        # Default recipient of a generic page ("page the oncall"): the newest
        # on-call rotation page of this corpus, used only while it is fresh.
        self.oncall_rotation = rotation_from_docs(
            self.corpus.docs, now=self.corpus.now, sla_for=self.sla_for
        )
        self._doc_texts: dict[str, list[str]] = {}
        for c in self.corpus.chunks:
            self._doc_texts.setdefault(c.doc_id, []).append(c.text)

    def grounding_gap(self, query: str, chunks: list[Chunk], *, combined: bool = False) -> GroundingGap:
        """Closest chunk (or the combined fresh evidence) and the query terms it lacks."""
        if not chunks:
            return GroundingGap(None, self.grounder.missing_terms(query, ""), 0.0)
        if combined:
            parts = [f"{c.title} {c.text}" for c in chunks]
            cov, _ = self.grounder.coverage(query, " ".join(parts), evidence_parts=parts)
            return GroundingGap(
                chunks[0].doc_id,
                self.grounder.missing_terms(query, " ".join(parts), evidence_parts=parts),
                cov,
            )
        best, best_cov = chunks[0], -1.0
        for chunk in chunks:
            cov, _ = self.grounder.chunk_support(query, f"{chunk.title} {chunk.text}")
            if cov > best_cov:
                best, best_cov = chunk, cov
        return GroundingGap(best.doc_id, self.grounder.missing_terms(query, f"{best.title} {best.text}"), best_cov)

    def _explain_context(
        self, query: str, retrieved: list[Chunk], fresh_hits: list[Chunk], cited_docs: dict, canary_scan, pii_scan
    ) -> ExplainContext:
        canary_docs: list[str] = []
        if getattr(canary_scan, "has_leak", False):
            held = [d for t in canary_scan.leaked for d in self.canary_registry.doc_ids_for(t)]
            canary_docs = [d for d in dict.fromkeys(held) if d in cited_docs] or list(dict.fromkeys(held))
        pii_docs: list[str] = []
        if getattr(pii_scan, "should_refuse", False):
            pii_docs = [d for d in cited_docs if detect_pii(" ".join(self._doc_texts.get(d, ())))]
        return ExplainContext(
            gap_fn=lambda: self.grounding_gap(query, retrieved),
            answer_gap_fn=lambda: self.grounding_gap(query, fresh_hits, combined=True) if fresh_hits else None,
            canary_doc_ids=canary_docs,
            pii_doc_ids=pii_docs,
            registry=self.registry,
            query=query,
        )

    def sla_for(self, source_system: str) -> float:
        """Resolve the max_age_hours that applies to a source_system."""
        return resolve_max_age(
            source_system,
            table=self.sla_table,
            global_default_hours=self.config.max_age_hours,
            use_source_slas=self.config.use_source_slas,
        )

    def ask(self, query: str, *, session_id: str | None = None) -> CopilotResult:
        started = time.perf_counter()
        cfg = self.config
        # Rankers and the extractive drafter see the normalized, filler-free,
        # typo-snapped query; grounding does its own term analysis on the raw
        # query; the canary gate keeps the raw query (identifiers exact-only).
        rq = self.retriever.rewrite_query(query)
        retrieved = self.retriever.search(rq)
        bm25_hits = self.retriever.search_bm25(rq, top_k=cfg.disagreement_top_k)
        dense_hits = self.retriever.search_dense(rq, top_k=cfg.disagreement_top_k)
        disagreement = assess_disagreement(
            bm25_hits,
            dense_hits,
            top_k=cfg.disagreement_top_k,
            threshold=cfg.disagreement_jaccard_threshold,
            dense_name=self.retriever.last_dense_name,
        )

        sla_lookup = self.sla_for if cfg.use_source_slas else None
        freshness = annotate(
            retrieved,
            None if sla_lookup else cfg.max_age_hours,
            sla_lookup=sla_lookup,
        )
        supporting, best_support = supporting_chunks(
            query,
            retrieved,
            self.grounder,
            cfg.grounding_threshold,
        )
        fresh_hits = fresh_only(
            supporting,
            None if sla_lookup else cfg.max_age_hours,
            sla_lookup=sla_lookup,
        )

        draft = ""
        grounding = None
        # Draft/ground only when disagreement will not refuse — still compute
        # grounding for inspectability when we disagree, but skip extractive work
        # is optional; we compute for traces either way when fresh hits exist.
        if fresh_hits:
            draft = extractive_answer(
                rq,
                fresh_hits,
                max_sentences=cfg.max_answer_sentences,
            )
            grounding = self.grounder.check(query, fresh_hits, draft)
        elif supporting or retrieved:
            grounding = self.grounder.check(query, supporting or retrieved, draft)

        request_cost = _cost_units(
            len(retrieved), cfg.use_dense, cfg.use_disagreement_gate
        )
        spent_before = self.ledger.spent(session_id)
        budget_active = bool(cfg.use_budget_gate and session_id)

        canary_scan = scan_answer(draft, query, self.canary_registry)
        # Quarantine is document-scoped: a cited page that holds a secret in
        # another paragraph is still a secret-bearing page.
        cited_docs = dict.fromkeys(c.doc_id for c in fresh_hits)
        semantic_used = bool(grounding is not None and grounding.semantic_rescued)
        translation_used = bool(grounding is not None and grounding.translation_rescued)
        passage_used = bool(grounding is not None and grounding.passage_rescued)
        strict_rescue = (
            (semantic_used and cfg.semantic_grounding_strict)
            or (translation_used and cfg.answer_support_strict)
            or (passage_used and cfg.passage_support_strict)
        )
        if strict_rescue and not canary_scan.has_leak:
            # Safety tightening for the semantic grounding backoff: an answer
            # that leans on embedding support must not cite a page holding an
            # unjustified canary, even when the extractive draft happened to
            # skip that paragraph (see README "Real embeddings", g35-synonym).
            doc_scan = scan_answer(
                " ".join(t for d in cited_docs for t in self._doc_texts.get(d, ())),
                query,
                self.canary_registry,
            )
            if doc_scan.has_leak:
                canary_scan = doc_scan
        pii_scan = scan_answer_pii(
            draft,
            rq,
            evidence_texts=[t for d in cited_docs for t in self._doc_texts.get(d, ())],
        )
        intent = (
            classify_write_intent(
                query,
                registry=self.registry,
                typo_tolerance=cfg.typo_tolerance,
                mood_detection=cfg.write_mood_detection,
                prototypes=self.write_prototypes,
                min_confidence=cfg.write_min_confidence,
                phrasal=cfg.write_phrasal_parser,
                cli_verbs=cfg.write_ops_cli_verbs,
                require_registered=cfg.write_require_registered_target,
                oncall=self.oncall_rotation,
            )
            if cfg.use_hitl_write_gate
            else None
        )
        write_intent = proposal_from_intent(intent) if intent is not None else None
        ambiguous_write = intent if intent is not None and intent.status == AMBIGUOUS else None
        policy = decide(
            retrieved,
            freshness,
            supporting,
            fresh_hits,
            grounding,
            max_age_hours=cfg.max_age_hours,
            best_support=best_support,
            support_floor=cfg.support_floor,
            use_source_slas=cfg.use_source_slas,
            disagreement=disagreement,
            use_disagreement_gate=cfg.use_disagreement_gate,
            use_budget_gate=budget_active,
            session_spent=spent_before,
            request_cost=request_cost,
            session_budget=cfg.session_budget_cost_units,
            session_id=session_id,
            canary_scan=canary_scan,
            use_canary_gate=cfg.use_canary_gate,
            write_intent=write_intent,
            use_hitl_write_gate=cfg.use_hitl_write_gate,
            pii_scan=pii_scan,
            use_pii_gate=cfg.use_pii_gate,
            ambiguous_write=ambiguous_write,
            explain=self._explain_context(query, retrieved, fresh_hits, cited_docs, canary_scan, pii_scan),
        )

        proposed_write = None
        if policy.decision is Decision.ANSWER:
            if getattr(pii_scan, "action", "pass") == "redact":
                answer = pii_scan.redacted_text
            else:
                answer = draft
            cited = list(dict.fromkeys(c.doc_id for c in fresh_hits))
        elif policy.decision is Decision.PROPOSE_WRITE and write_intent is not None:
            evidence_ids = list(
                dict.fromkeys(c.doc_id for c in (fresh_hits or supporting or retrieved))
            )
            record = self.hitl.propose(
                write_intent,
                actor="copilot",
                evidence_ids=evidence_ids,
            )
            proposed_write = record.as_dict()
            answer = render_refusal(policy.decision, policy.reason)
            cited = evidence_ids
        else:
            # Refusal reasons can quote the parsed target (user text); run the
            # same redaction the explanation gets before it is rendered.
            policy.reason, _ = redact_string(policy.reason, context=(query,))
            answer = render_refusal(policy.decision, policy.reason)
            cited = []

        spent_after = (
            self.ledger.record(session_id, request_cost) if session_id else spent_before
        )

        latency_ms = (time.perf_counter() - started) * 1000.0
        return CopilotResult(
            query=query,
            decision=policy.decision,
            reason=policy.reason,
            answer=answer,
            retrieved=retrieved,
            fresh_hits=fresh_hits,
            freshness=freshness,
            grounding=grounding,
            latency_ms=latency_ms,
            approx_cost_units=request_cost,
            cited_ids=cited,
            disagreement=disagreement.as_dict(),
            session_id=session_id,
            session_spent_before=spent_before,
            session_spent_after=spent_after,
            session_budget=cfg.session_budget_cost_units if budget_active else None,
            canary=canary_scan.as_dict(),
            proposed_write=proposed_write,
            pii_detected=bool(pii_scan.pii_detected),
            redactions_count=int(pii_scan.redactions_count),
            pii=pii_scan.as_dict(),
            write_intent=intent.parse_dict() if intent is not None else None,
            explanation=policy.explanation,
        )


def run_query(
    query: str,
    *,
    config: CopilotConfig | None = None,
    path: str | Path | None = None,
    now: datetime | str | None = None,
    session_id: str | None = None,
) -> CopilotResult:
    """Convenience wrapper used by scripts and tests."""
    cfg = config or CopilotConfig()
    copilot = Copilot(config=cfg, path=path, now=parse_clock(now))
    return copilot.ask(query, session_id=session_id)
