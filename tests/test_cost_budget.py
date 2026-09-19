"""Session cost ledger + REFUSE_BUDGET independence from freshness/disagreement."""

from __future__ import annotations

from ops_copilot import Copilot, CopilotConfig
from ops_copilot.cost_budget import SessionCostLedger
from ops_copilot.disagreement import DisagreementResult
from ops_copilot.freshness import annotate
from ops_copilot.policy import decide
from ops_copilot.types import Decision, GroundingResult

from conftest import make_chunk


def test_ledger_accumulate_and_exceed() -> None:
    ledger = SessionCostLedger()
    assert ledger.spent("s1") == 0.0
    assert not ledger.would_exceed("s1", 2.0, budget=5.0)
    ledger.record("s1", 3.0)
    assert ledger.spent("s1") == 3.0
    assert ledger.would_exceed("s1", 2.5, budget=5.0)
    assert not ledger.would_exceed(None, 99.0, budget=5.0)


def test_ledger_seed_and_reset() -> None:
    ledger = SessionCostLedger()
    ledger.seed("trap", 4.0)
    assert ledger.spent("trap") == 4.0
    ledger.reset("trap")
    assert ledger.spent("trap") == 0.0


def _grounded() -> GroundingResult:
    return GroundingResult(
        passed=True,
        query_coverage=0.9,
        answer_coverage=0.9,
        threshold=0.52,
        overlap_tokens=["checkout"],
    )


def test_policy_budget_refuses_before_answer() -> None:
    chunks = [make_chunk("fresh", hours_old=2.0)]
    decision = decide(
        chunks,
        annotate(chunks, 48.0),
        supporting=chunks,
        fresh_supporting=chunks,
        grounding=_grounded(),
        max_age_hours=48.0,
        best_support=0.9,
        use_budget_gate=True,
        session_spent=4.0,
        request_cost=2.0,
        session_budget=5.0,
        session_id="s-budget",
    )
    assert decision.decision is Decision.REFUSE_BUDGET
    assert "budget" in decision.reason.lower()


def test_policy_budget_beats_disagreement() -> None:
    """Budget gate fires before disagreement when both would refuse."""
    chunks = [make_chunk("fresh", hours_old=2.0)]
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
        fresh_supporting=chunks,
        grounding=_grounded(),
        max_age_hours=48.0,
        best_support=0.9,
        disagreement=disagreement,
        use_disagreement_gate=True,
        use_budget_gate=True,
        session_spent=4.5,
        request_cost=1.0,
        session_budget=5.0,
        session_id="s-both",
    )
    assert decision.decision is Decision.REFUSE_BUDGET


def test_policy_no_session_skips_budget() -> None:
    chunks = [make_chunk("fresh", hours_old=2.0)]
    decision = decide(
        chunks,
        annotate(chunks, 48.0),
        supporting=chunks,
        fresh_supporting=chunks,
        grounding=_grounded(),
        max_age_hours=48.0,
        best_support=0.9,
        use_budget_gate=True,
        session_spent=99.0,
        request_cost=99.0,
        session_budget=5.0,
        session_id=None,
    )
    assert decision.decision is Decision.ANSWER


def test_pipeline_session_trips_independently() -> None:
    """Same ANSWER query refuses under budget without changing freshness path."""
    bot = Copilot(config=CopilotConfig(session_budget_cost_units=5.0))
    q = "What is the current checkout p99 latency?"
    ok = bot.ask(q)  # no session → no budget gate
    assert ok.decision is Decision.ANSWER

    bot.ledger.seed("hire-demo", 4.0)
    refused = bot.ask(q, session_id="hire-demo")
    assert refused.decision is Decision.REFUSE_BUDGET
    assert refused.session_spent_before == 4.0
    assert refused.session_spent_after > 4.0
    assert refused.approx_cost_units > 0
    assert refused.cited_ids == []


def test_pipeline_accumulates_across_turns() -> None:
    bot = Copilot(config=CopilotConfig(session_budget_cost_units=5.0))
    sid = "multi-turn"
    q = "What is the current checkout p99 latency?"
    first = bot.ask(q, session_id=sid)
    assert first.decision is Decision.ANSWER
    second = bot.ask(q, session_id=sid)
    # Second may still answer if 2 * cost <= 5; third should trip.
    third = bot.ask(q, session_id=sid)
    decisions = {first.decision, second.decision, third.decision}
    assert Decision.REFUSE_BUDGET in decisions or third.decision is Decision.REFUSE_BUDGET
    assert bot.ledger.spent(sid) >= first.approx_cost_units
