from __future__ import annotations

from ops_copilot.freshness import annotate, fresh_only
from ops_copilot.policy import decide
from ops_copilot.types import Decision, GroundingResult

from conftest import make_chunk


def _grounded() -> GroundingResult:
    return GroundingResult(
        passed=True,
        query_coverage=0.9,
        answer_coverage=0.9,
        threshold=0.52,
        overlap_tokens=["checkout"],
    )


def _ungrounded(cov: float = 0.2) -> GroundingResult:
    return GroundingResult(
        passed=False,
        query_coverage=cov,
        answer_coverage=0.9,
        threshold=0.52,
        overlap_tokens=[],
    )


def test_no_evidence_empty_retrieve() -> None:
    decision = decide([], [], [], [], None, max_age_hours=48.0)
    assert decision.decision is Decision.REFUSE_NO_EVIDENCE


def test_retrieved_junk_is_no_evidence() -> None:
    chunks = [make_chunk("noise", hours_old=2.0, text="unrelated prometheus scrape")]
    decision = decide(
        chunks,
        annotate(chunks, 48.0),
        supporting=[],
        fresh_supporting=[],
        grounding=_ungrounded(0.05),
        max_age_hours=48.0,
        best_support=0.05,
        support_floor=0.20,
    )
    assert decision.decision is Decision.REFUSE_NO_EVIDENCE


def test_partial_support_is_ungrounded() -> None:
    chunks = [make_chunk("flag", hours_old=2.0, text="checkout_retry is enabled")]
    decision = decide(
        chunks,
        annotate(chunks, 48.0),
        supporting=[],
        fresh_supporting=[],
        grounding=_ungrounded(0.35),
        max_age_hours=48.0,
        best_support=0.35,
        support_floor=0.20,
    )
    assert decision.decision is Decision.REFUSE_UNGROUNDED


def test_all_supporting_stale_refuses_even_if_would_ground() -> None:
    chunks = [make_chunk("stale", hours_old=200.0, text="redis maxmemory-policy is allkeys-lru")]
    freshness = annotate(chunks, 48.0)
    decision = decide(
        chunks,
        freshness,
        supporting=chunks,
        fresh_supporting=[],
        grounding=_grounded(),
        max_age_hours=48.0,
        best_support=0.9,
    )
    assert decision.decision is Decision.REFUSE_STALE
    assert "freshness SLA" in decision.reason


def test_fresh_supporting_and_grounded_answers() -> None:
    chunks = [make_chunk("fresh", hours_old=2.0)]
    decision = decide(
        chunks,
        annotate(chunks, 48.0),
        supporting=chunks,
        fresh_supporting=chunks,
        grounding=_grounded(),
        max_age_hours=48.0,
        best_support=0.9,
    )
    assert decision.decision is Decision.ANSWER


def test_fresh_supporting_but_answer_ungrounded() -> None:
    chunks = [make_chunk("fresh", hours_old=2.0)]
    decision = decide(
        chunks,
        annotate(chunks, 48.0),
        supporting=chunks,
        fresh_supporting=chunks,
        grounding=_ungrounded(0.6),
        max_age_hours=48.0,
        best_support=0.6,
    )
    assert decision.decision is Decision.REFUSE_UNGROUNDED


def test_tangential_fresh_cannot_launder_stale_support() -> None:
    stale = make_chunk("stale", hours_old=400.0, text="redis maxmemory-policy is allkeys-lru")
    fresh = make_chunk("fresh", hours_old=2.0, text="redis checkout-pool is 49 of 50")
    chunks = [stale, fresh]
    # Only the stale chunk actually supports "maxmemory-policy".
    decision = decide(
        chunks,
        annotate(chunks, 48.0),
        supporting=[stale],
        fresh_supporting=fresh_only([stale], 48.0),
        grounding=_grounded(),
        max_age_hours=48.0,
        best_support=0.85,
    )
    assert decision.decision is Decision.REFUSE_STALE


def test_policy_matrix_labels() -> None:
    stale = [make_chunk("s", hours_old=99)]
    fresh = [make_chunk("f", hours_old=1)]
    got = {
        "empty": decide([], [], [], [], None, max_age_hours=48).decision,
        "stale": decide(
            stale, annotate(stale, 48), stale, [], _grounded(), max_age_hours=48, best_support=0.9
        ).decision,
        "ungrounded": decide(
            fresh, annotate(fresh, 48), [], [], _ungrounded(0.3), max_age_hours=48, best_support=0.3
        ).decision,
        "ok": decide(
            fresh, annotate(fresh, 48), fresh, fresh, _grounded(), max_age_hours=48, best_support=0.9
        ).decision,
    }
    assert got["empty"] is Decision.REFUSE_NO_EVIDENCE
    assert got["stale"] is Decision.REFUSE_STALE
    assert got["ungrounded"] is Decision.REFUSE_UNGROUNDED
    assert got["ok"] is Decision.ANSWER


def test_disagreement_refuses_after_freshness() -> None:
    from ops_copilot.disagreement import DisagreementResult

    chunks = [make_chunk("fresh", hours_old=2.0)]
    disagreement = DisagreementResult(
        jaccard=0.0,
        threshold=1.0,
        top_k=1,
        bm25_ids=("doc_a",),
        dense_ids=("doc_b",),
        agreed=False,
    )
    decision = decide(
        chunks,
        annotate(chunks, 48.0),
        supporting=chunks,
        fresh_supporting=chunks,
        grounding=_grounded(),
        max_age_hours=48.0,
        best_support=0.9,
        disagreement=disagreement,
        use_disagreement_gate=True,
    )
    assert decision.decision is Decision.REFUSE_DISAGREE
    assert "jaccard" in decision.reason


def test_stale_beats_disagreement() -> None:
    """Freshness gate fires before disagreement."""
    from ops_copilot.disagreement import DisagreementResult

    chunks = [make_chunk("stale", hours_old=200.0)]
    disagreement = DisagreementResult(
        jaccard=0.0,
        threshold=1.0,
        top_k=1,
        bm25_ids=("a",),
        dense_ids=("b",),
        agreed=False,
    )
    decision = decide(
        chunks,
        annotate(chunks, 48.0),
        supporting=chunks,
        fresh_supporting=[],
        grounding=_grounded(),
        max_age_hours=48.0,
        best_support=0.9,
        disagreement=disagreement,
        use_disagreement_gate=True,
    )
    assert decision.decision is Decision.REFUSE_STALE


def test_budget_beats_stale_when_both_apply() -> None:
    """Budget is checked first — over-budget sessions do not surface REFUSE_STALE."""
    chunks = [make_chunk("stale", hours_old=200.0)]
    decision = decide(
        chunks,
        annotate(chunks, 48.0),
        supporting=chunks,
        fresh_supporting=[],
        grounding=_grounded(),
        max_age_hours=48.0,
        best_support=0.9,
        use_budget_gate=True,
        session_spent=5.0,
        request_cost=1.0,
        session_budget=5.0,
        session_id="over",
    )
    assert decision.decision is Decision.REFUSE_BUDGET
