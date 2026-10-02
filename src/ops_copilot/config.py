"""Frozen clock and default policy knobs.

A frozen evaluation clock keeps ages, golden labels, and CI deterministic.
Override ``now`` or ``OPS_COPILOT_NOW`` only for live demos.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import datetime, timezone

EVAL_CLOCK = datetime(2026, 9, 13, 0, 0, 0, tzinfo=timezone.utc)
RNG_SEED = 42


def parse_clock(value: str | datetime | None) -> datetime:
    """Parse an ISO-8601 clock, defaulting to the frozen eval clock."""
    if value is None:
        env = os.environ.get("OPS_COPILOT_NOW")
        if env:
            return parse_clock(env)
        return EVAL_CLOCK
    if isinstance(value, datetime):
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


@dataclass(frozen=True)
class CopilotConfig:
    """Policy and retrieval knobs for a single copilot instance."""

    max_age_hours: float = 48.0
    # When True, freshness uses per-source SLAs (see config/source_slas.yaml)
    # with max_age_hours as the fallback for unknown sources. When False,
    # every source shares max_age_hours (v0 global-only behaviour).
    use_source_slas: bool = True
    source_sla_path: str | None = None
    top_k: int = 5
    min_retrieve_score: float = 1.15
    min_cosine: float = 0.08
    grounding_threshold: float = 0.52
    support_floor: float = 0.15
    hybrid_dense_weight: float = 0.30
    use_dense: bool = True
    max_answer_sentences: int = 2
    rng_seed: int = RNG_SEED
    # Disagreement routing: compare BM25 vs the dense retriever (TitleHashDenseStub,
    # or the MiniLM EmbeddingDenseRetriever when embeddings are on) top-k doc ids.
    use_disagreement_gate: bool = True
    disagreement_top_k: int = 1
    # Agreed when Jaccard >= threshold. With top_k=1, threshold=1.0 means
    # the two retrievers must share the same top doc_id.
    disagreement_jaccard_threshold: float = 1.0
    # Session cost budget: accumulate approx_cost_units per session_id.
    # When spent + this request would exceed the budget, policy emits REFUSE_BUDGET.
    # Gate applies only when a session_id is provided (API header/body or ask()).
    use_budget_gate: bool = True
    # Default allows ~2 typical hybrid+disagreement queries then trips on the 3rd.
    session_budget_cost_units: float = 5.0
    # Prompt-injection canary farm: refuse when draft echoes unjustified CNRY tokens.
    use_canary_gate: bool = True
    canary_registry_path: str | None = None
    # HITL write gate: imperative writes become PROPOSE_WRITE (pending) until human approve.
    use_hitl_write_gate: bool = True
    # Structured write-intent parser (write_intent.py). Mood detection off is
    # the "lexicon parser only" ablation (first ontology verb anywhere is an
    # instruction). Proposals need at least write_min_confidence; anything
    # write-shaped below it, or without a target, is REFUSE_AMBIGUOUS_WRITE.
    write_mood_detection: bool = True
    write_min_confidence: float = 0.65
    # PII/secret redaction gate: refuse unauthorized leaks; mask authorized contacts.
    use_pii_gate: bool = True
    # Typo tolerance: unknown plain words snap to a unique corpus word within
    # one edit (identifiers exact-only). Off reproduces exact-match behaviour.
    typo_tolerance: bool = True
    # Corpus-side synonym/lemma groups (synonyms.py) for grounding, retrieval
    # rewrite, and restart verbs. Off = the ablation reported in the README.
    use_synonyms: bool = True
    # Offline semantic backoff (semantic.py): a corpus PPMI/SVD embedding plus
    # char-trigram similarity maps an otherwise unplaceable query word to a
    # few corpus words, for grounding and the retrieval rewrite. Default
    # decided by the held-out synonym rows (README "Held-out synonyms").
    use_semantic_backoff: bool = False
    semantic_char_ngrams: bool = True
    semantic_min_similarity: float = 0.60
    semantic_max_neighbours: int = 1
    # Optional sentence embeddings (embeddings.py, extra "[embed]").
    # "off" keeps the offline title-hash dense stub and lexical-only grounding
    # (the CI default); "frozen" reads the committed float16 fixtures in
    # data/embeddings/ (no model needed); "model" runs all-MiniLM-L6-v2 from the
    # local Hugging Face cache; "auto" uses the model if cached, else the fixture.
    embedding_backend: str = "off"
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    embedding_allow_download: bool = False
    # With a backend on: use it as the dense retriever in the disagreement gate.
    embed_dense_retriever: bool = True
    # With a backend on: semantic grounding backoff (grounding.EmbeddingSupport).
    # Threshold and max_terms come from scripts/calibrate_semantic_grounding.py
    # (clean golden + dev synonym rows only).
    embed_semantic_grounding: bool = True
    semantic_grounding_threshold: float = 0.45
    semantic_grounding_max_terms: int = 1
    # Safety tightening (README "Real embeddings"): rescue only wh-questions
    # whose every other salient term is matched lexically, and refuse a rescued
    # answer whose cited page holds an unjustified canary. Off = unsafe ablation.
    semantic_grounding_strict: bool = True
