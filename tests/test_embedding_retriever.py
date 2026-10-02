"""MiniLM dense retriever in the disagreement gate (frozen fixture, offline)."""

from __future__ import annotations

from dataclasses import replace

import pytest

from ops_copilot import Copilot, CopilotConfig
from ops_copilot.eval import load_golden
from ops_copilot.retrieve import EmbeddingDenseRetriever
from ops_copilot.types import Decision

FROZEN = replace(CopilotConfig(), embedding_backend="frozen")
DISAGREE_TRAPS = {
    "What is the sidecar mesh mtls handshake budget?": "bait_mesh_",
    "What is the checkout canary stickiness salt?": "bait_stick_",
    "What is the payments WAL checkpoint cadence?": "bait_wal_",
    "What is the checkout trace sample reservoir size?": "bait_res_",
}


@pytest.fixture(scope="module")
def bot() -> Copilot:
    return Copilot(config=FROZEN)


def test_embedding_backend_swaps_the_dense_retriever(bot: Copilot) -> None:
    assert isinstance(bot.retriever.dense_embed, EmbeddingDenseRetriever)
    assert bot.retriever.dense_embed.n_missing_passages == 0
    off = Copilot(config=replace(FROZEN, embed_dense_retriever=False))
    assert off.retriever.dense_embed is None


@pytest.mark.parametrize("query,bait", sorted(DISAGREE_TRAPS.items()))
def test_title_decoy_traps_still_disagree_with_minilm(bot: Copilot, query: str, bait: str) -> None:
    res = bot.ask(query)
    assert res.decision is Decision.REFUSE_DISAGREE
    assert res.disagreement["dense_name"] == "minilm_dense"
    assert res.disagreement["dense_ids"][0].startswith(bait)
    assert "minilm_dense" in res.reason


def test_minilm_agrees_with_bm25_on_every_clean_answer(bot: Copilot) -> None:
    for case in load_golden():
        if case["expect_decision"] != "ANSWER":
            continue
        res = bot.ask(str(case["query"]))
        assert res.disagreement["agreed"], (case["query"], res.disagreement)


def test_query_miss_falls_back_to_the_title_hash_stub(bot: Copilot) -> None:
    rq = bot.retriever.rewrite_query("an unseen question about kafka consumer offsets")
    hits = bot.retriever.search_dense(rq, top_k=1)
    assert bot.retriever.last_dense_name == "title_hash_dense_stub (embedding miss)"
    assert [h.doc_id for h in hits] == [
        h.doc_id for h in bot.retriever.search_dense_stub(rq, top_k=1)
    ]


def test_dense_ranking_is_stable_and_scored(bot: Copilot) -> None:
    rq = bot.retriever.rewrite_query("What is the current checkout p99 latency?")
    a = bot.retriever.search_dense(rq, top_k=5)
    b = bot.retriever.search_dense(rq, top_k=5)
    assert [h.chunk_id for h in a] == [h.chunk_id for h in b]
    assert all(0.0 < h.dense <= 1.0 + 1e-6 for h in a)
    assert [h.dense for h in a] == sorted((h.dense for h in a), reverse=True)
