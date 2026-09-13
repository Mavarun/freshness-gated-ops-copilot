from __future__ import annotations

from ops_copilot.grounding import Grounder

from conftest import make_chunk


def _grounder() -> Grounder:
    texts = [
        "checkout p99 latency is 2410 milliseconds in us-east-1",
        "feature flag checkout_retry is enabled at 15 percent canary",
        "do not store production passwords in slack",
    ]
    return Grounder(texts, threshold=0.52)


def test_supported_query_passes() -> None:
    g = _grounder()
    evidence = [make_chunk(text="checkout p99 latency is 2410 milliseconds in us-east-1")]
    answer = "checkout p99 latency is 2410 milliseconds in us-east-1 [sources: doc]"
    result = g.check("What is the checkout p99 latency?", evidence, answer)
    assert result.passed is True
    assert result.query_coverage >= 0.52


def test_unsupported_query_fails() -> None:
    g = _grounder()
    evidence = [make_chunk(text="feature flag checkout_retry is enabled at 15 percent canary")]
    answer = "feature flag checkout_retry is enabled at 15 percent canary [sources: doc]"
    result = g.check(
        "What is the rollback procedure for the checkout_retry feature flag?",
        evidence,
        answer,
    )
    assert result.passed is False


def test_empty_evidence_fails() -> None:
    g = _grounder()
    result = g.check("checkout p99 latency", [], "anything")
    assert result.passed is False


def test_empty_answer_fails_even_if_query_overlaps() -> None:
    g = _grounder()
    evidence = [make_chunk(text="checkout p99 latency is 2410 milliseconds")]
    result = g.check("What is the checkout p99 latency?", evidence, "")
    assert result.passed is False


def test_answer_must_overlap_evidence() -> None:
    g = _grounder()
    evidence = [make_chunk(text="checkout p99 latency is 2410 milliseconds")]
    hallucinated = "the cluster was rebuilt by the moon landing team yesterday"
    result = g.check("What is the checkout p99 latency?", evidence, hallucinated)
    assert result.answer_coverage < 0.50
    assert result.passed is False


def test_oov_tokens_weigh_more_than_corpus_regulars() -> None:
    g = _grounder()
    evidence = [make_chunk(text="checkout p99 latency is 2410 milliseconds")]
    cov_ok, _ = g.coverage("checkout p99 latency", evidence[0].text)
    cov_trap, overlap = g.coverage(
        "chargeback playbook for checkout p99", evidence[0].text
    )
    assert cov_ok > cov_trap
    assert "chargeback" not in overlap
