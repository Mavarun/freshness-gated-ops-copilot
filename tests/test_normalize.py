"""Shared normalizer: one canonical string for BM25, dense stub, grounding, gates."""

from __future__ import annotations

import pytest

from ops_copilot import Copilot
from ops_copilot.pii_redact import query_authorizes_contact
from ops_copilot.text import normalize_text, tokenize
from ops_copilot.types import Decision
from ops_copilot.write_actions import detect_write_intent


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("What is the current checkout p99 latency?", "what is the current checkout p99 latency"),
        ("latency p99?", "latency p99"),
        ("Slack #inc-4821 on-call thread", "slack inc-4821 on-call thread"),
        ("INC-3104 checkout latency (resolved)", "inc-3104 checkout latency resolved"),
        ("patch redis.maxmemory-policy to allkeys-lru.", "patch redis.maxmemory-policy to allkeys-lru"),
        ("Is checkout_retry on?!", "is checkout_retry on"),
        ("What\u2019s the procedure\u2014restart?", "what is the procedure restart"),
        ("caf\u00e9 CHECKOUT\u2011api", "cafe checkout-api"),
        ("--edge-- _case_ .dots.", "edge case dots"),
    ],
)
def test_normalize_text_cases(raw: str, expected: str) -> None:
    assert normalize_text(raw) == expected


def test_normalize_is_idempotent_and_keeps_identifiers() -> None:
    raw = "Page the ON-CALL for INC-4821?! checkout_retry, p99, redis.maxmemory-policy."
    once = normalize_text(raw)
    assert normalize_text(once) == once
    for ident in ("on-call", "inc-4821", "checkout_retry", "p99", "redis.maxmemory-policy"):
        assert ident in once.split()


def test_tokenize_ignores_stuck_on_punctuation() -> None:
    assert tokenize("latency p99?") == tokenize("latency p99") == ["latency", "p99"]


def test_dense_stub_top1_does_not_depend_on_question_mark_position(copilot: Copilot) -> None:
    """g00-word_order regression: '?' moved from 'latency' to 'p99' flipped top-1."""
    a = copilot.retriever.search_dense_stub("What is the current checkout p99 latency?", top_k=1)
    b = copilot.retriever.search_dense_stub("What the is current checkout latency p99?", top_k=1)
    c = copilot.retriever.search_dense_stub("what the is current checkout latency p99", top_k=1)
    assert a[0].doc_id == b[0].doc_id == c[0].doc_id


def test_bm25_scores_identical_with_and_without_punctuation(copilot: Copilot) -> None:
    a = copilot.retriever.search_bm25("Redis maxmemory-policy?", top_k=3)
    b = copilot.retriever.search_bm25("redis maxmemory-policy", top_k=3)
    assert [h.doc_id for h in a] == [h.doc_id for h in b]
    assert [round(h.bm25, 9) for h in a] == [round(h.bm25, 9) for h in b]


def test_word_order_p99_question_now_answers(copilot: Copilot) -> None:
    result = copilot.ask("What the is current checkout latency p99?")
    assert result.decision is Decision.ANSWER


def test_gates_see_normalized_text() -> None:
    assert detect_write_intent("PLEASE RESTART THE CHECKOUT-API SERVICE NOW!") is not None
    assert query_authorizes_contact("What is the vault-transit key rotation Contact-Email?") is False
    assert query_authorizes_contact("What is the vault-transit key rotation CONTACT EMAIL?!")
