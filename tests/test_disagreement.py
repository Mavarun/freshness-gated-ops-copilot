"""Agreement / disagreement matrix for BM25 vs TitleHashDenseStub."""

from __future__ import annotations

from ops_copilot import Copilot, CopilotConfig
from ops_copilot.disagreement import assess_disagreement, jaccard
from ops_copilot.types import Decision

from conftest import make_chunk


def test_jaccard_identical_and_disjoint() -> None:
    assert jaccard({"a"}, {"a"}) == 1.0
    assert jaccard({"a"}, {"b"}) == 0.0
    assert jaccard(set(), set()) == 1.0
    assert jaccard({"a", "b"}, {"b", "c"}) == 1.0 / 3.0


def test_assess_top1_agreement() -> None:
    a = [make_chunk("doc_a", hours_old=1.0)]
    b = [make_chunk("doc_a", hours_old=1.0)]
    result = assess_disagreement(a, b, top_k=1, threshold=1.0)
    assert result.agreed is True
    assert result.jaccard == 1.0


def test_assess_top1_disagreement() -> None:
    a = [make_chunk("doc_a", hours_old=1.0)]
    b = [make_chunk("doc_b", hours_old=1.0)]
    result = assess_disagreement(a, b, top_k=1, threshold=1.0)
    assert result.disagreed is True
    assert result.jaccard == 0.0


def test_agreement_matrix_on_fixture_chunks() -> None:
    """Explicit matrix: same ids agree; disjoint disagree; partial soft-threshold."""
    shared = [make_chunk("shared", hours_old=1.0), make_chunk("only_a", hours_old=1.0)]
    other = [make_chunk("shared", hours_old=1.0), make_chunk("only_b", hours_old=1.0)]
    strict = assess_disagreement(shared, other, top_k=2, threshold=1.0)
    soft = assess_disagreement(shared, other, top_k=2, threshold=0.3)
    assert strict.disagreed is True  # jaccard = 1/3
    assert soft.agreed is True


def test_mesh_trap_refuses_disagree(copilot: Copilot) -> None:
    result = copilot.ask("What is the sidecar mesh mtls handshake budget?")
    assert result.decision is Decision.REFUSE_DISAGREE
    assert result.disagreement is not None
    assert result.disagreement["agreed"] is False
    assert result.cited_ids == []


def test_bm25_only_answers_mesh_trap() -> None:
    bot = Copilot(config=CopilotConfig(use_disagreement_gate=False))
    result = bot.ask("What is the sidecar mesh mtls handshake budget?")
    assert result.decision is Decision.ANSWER
    assert "250" in result.answer


def test_happy_path_still_answers_with_gate(copilot: Copilot) -> None:
    result = copilot.ask("What is the current checkout p99 latency?")
    assert result.decision is Decision.ANSWER
    assert result.disagreement is not None
    assert result.disagreement["agreed"] is True


def test_search_bm25_and_dense_stub_expose_separate_rankings(copilot: Copilot) -> None:
    q = "What is the checkout canary stickiness salt?"
    bm25 = copilot.retriever.search_bm25(q, top_k=1)
    dense = copilot.retriever.search_dense_stub(q, top_k=1)
    assert bm25 and dense
    assert bm25[0].doc_id != dense[0].doc_id
    assert copilot.retriever.dense_stub.name == "title_hash_dense_stub"
