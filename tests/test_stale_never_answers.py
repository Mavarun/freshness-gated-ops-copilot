from __future__ import annotations

from ops_copilot import Copilot, CopilotConfig, run_query
from ops_copilot.corpus import Corpus
from ops_copilot.freshness import age_passes
from ops_copilot.types import Decision

from conftest import make_doc

STALE_QUERIES = [
    "What is the Redis maxmemory-policy?",
    "How do we run the blue-green deploy procedure?",
    "What is the auth token TTL?",
    "How do I drain Kafka consumer lag on payments-worker?",
    "What was the Q1 checkout SLO target?",
    "How many replicas should payments-worker run?",
]


def test_golden_stale_queries_never_answer(copilot: Copilot) -> None:
    for query in STALE_QUERIES:
        result = copilot.ask(query)
        assert result.decision is not Decision.ANSWER, (query, result.decision, result.reason)
        assert result.decision is Decision.REFUSE_STALE, (query, result.decision, result.reason)
        assert result.cited_ids == []
        assert result.fresh_hits == []
        # Tangential fresh BM25 hits may exist; supporting evidence must be stale.
        assert result.retrieved, query


def test_tight_sla_refuses_otherwise_fresh_docs() -> None:
    # 30-minute SLA makes every corpus doc stale relative to the frozen clock.
    tight = Copilot(config=CopilotConfig(max_age_hours=0.25, use_source_slas=False))
    result = tight.ask("What is the current checkout p99 latency?")
    assert result.decision is Decision.REFUSE_STALE
    assert result.decision is not Decision.ANSWER


def test_stale_only_synthetic_corpus_cannot_answer() -> None:
    docs = [
        make_doc(
            "only_stale",
            hours_old=720.0,
            body="Redis maxmemory-policy is allkeys-lru. Maxmemory is 2gb.",
            title="Redis maxmemory-policy",
        )
    ]
    bot = Copilot(corpus=Corpus(docs=docs), config=CopilotConfig(max_age_hours=48.0))
    result = bot.ask("What is the Redis maxmemory-policy?")
    assert result.decision is Decision.REFUSE_STALE
    assert result.decision is not Decision.ANSWER


def test_run_query_wrapper_respects_sla() -> None:
    result = run_query("What is the auth token TTL?")
    assert result.decision is Decision.REFUSE_STALE


def test_answer_citations_are_always_fresh(copilot: Copilot) -> None:
    result = copilot.ask("Who is the primary on-call right now?")
    assert result.decision is Decision.ANSWER
    for chunk in result.fresh_hits:
        sla = copilot.sla_for(chunk.source_system)
        assert age_passes(chunk.age_hours, sla)
    for doc_id in result.cited_ids:
        ages = [c.age_hours for c in result.fresh_hits if c.doc_id == doc_id]
        assert ages
        for chunk in result.fresh_hits:
            if chunk.doc_id == doc_id:
                assert age_passes(chunk.age_hours, copilot.sla_for(chunk.source_system))
