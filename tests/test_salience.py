"""Grounding salience: filler never counts as a missing key term; unknown content does."""

from __future__ import annotations

import pytest

from ops_copilot import Copilot
from ops_copilot.grounding import Grounder
from ops_copilot.text import FILLER_WORDS, NON_SALIENT, STOPWORDS, content_tokens
from ops_copilot.types import Decision

POLITE = (
    "Could you please tell me",
    "Quick question:",
    "Hey team, sorry to bother you, but",
    "I was wondering,",
    "Would you kindly",
    "Hey, when you get a chance,",
    "I need you to",
)


def _grounder() -> Grounder:
    return Grounder(
        [
            "checkout p99 latency is 2410 milliseconds in us-east-1",
            "feature flag checkout_retry is enabled at 15 percent canary",
            "HPA utilization target is 70 percent on checkout-api",
        ]
    )


def test_filler_is_separate_from_stopwords_and_non_salient() -> None:
    assert FILLER_WORDS and not (FILLER_WORDS & {"not", "no", "never"})
    assert NON_SALIENT == STOPWORDS | FILLER_WORDS
    for word in ("hey", "team", "sorry", "bother", "wondering", "quick", "question", "kindly"):
        assert word not in content_tokens(f"{word} checkout latency")


@pytest.mark.parametrize("prefix", POLITE)
def test_polite_prefix_does_not_change_key_terms(prefix: str) -> None:
    g = _grounder()
    q = "what is the checkout p99 latency?"
    assert g.key_tokens(f"{prefix} {q}") == g.key_tokens(q)
    ev = "checkout p99 latency is 2410 milliseconds"
    assert g.coverage(f"{prefix} {q}", ev)[0] == pytest.approx(g.coverage(q, ev)[0])


def test_unknown_content_word_stays_salient_and_missing() -> None:
    g = _grounder()
    terms = {t.token: t.kind for t in g.terms("What millicore CPU request is on checkout-api?")}
    assert terms["millicore"] == "unknown"
    assert "millicore" in g.key_tokens("What millicore CPU request is on checkout-api?")
    assert not g.keys_supported(
        "What millicore CPU request is on checkout-api?",
        "HPA utilization target is 70 percent on checkout-api",
    )


def test_identifiers_and_numbers_are_salient() -> None:
    g = _grounder()
    kinds = {t.token: t.kind for t in g.terms("Is checkout_retry at 15 percent in us-east-1?")}
    assert kinds["checkout_retry"] == "identifier"
    assert kinds["15"] == "identifier"
    assert kinds["us-east-1"] == "identifier"
    assert kinds["percent"] == "known"


def test_missing_key_tokens_reports_only_salient_terms() -> None:
    g = _grounder()
    missing = g.missing_key_tokens(
        "Hey team, sorry to bother you, but what is the checkout rollback procedure?",
        "checkout p99 latency is 2410 milliseconds",
    )
    assert "rollback" in missing or "procedure" in missing
    assert not set(missing) & FILLER_WORDS


@pytest.mark.parametrize(
    "query",
    [
        "Hey team, sorry to bother you, but how many checkout-api replicas are running?",
        "I was wondering, is the checkout_retry feature flag enabled?",
        "Could you please tell me what is the Redis checkout-pool utilization?",
    ],
)
def test_polite_answer_queries_answer(copilot: Copilot, query: str) -> None:
    assert copilot.ask(query).decision is Decision.ANSWER


@pytest.mark.parametrize(
    ("query", "expected"),
    [
        ("Quick question: what is the rollback procedure for the checkout_retry feature flag?",
         Decision.REFUSE_UNGROUNDED),
        ("Hey team, sorry to bother you, but how do I reset the SAP payroll connector?",
         Decision.REFUSE_NO_EVIDENCE),
        ("I was wondering, what millicore CPU request is configured on checkout-api?",
         Decision.REFUSE_UNGROUNDED),
    ],
)
def test_polite_traps_still_refuse(copilot: Copilot, query: str, expected: Decision) -> None:
    assert copilot.ask(query).decision is expected
