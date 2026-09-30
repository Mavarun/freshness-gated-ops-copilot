"""Write gate: informational how-to exemption is position-independent."""

from __future__ import annotations

import pytest

from ops_copilot import Copilot
from ops_copilot.types import Decision
from ops_copilot.write_actions import WriteActionType, detect_write_intent

READS = [
    "Quick question: how do I restart the checkout-api service?",
    "Quick question: how do I restart checkout-api",
    "How I do restart checkout-api the service?",
    "Hey team, sorry to bother you, but how would we restart payments-worker?",
    "I was wondering, what's the procedure to restart checkout-api?",
    "Before the freeze, what is the process for restarting checkout-api?",
    "Steps to restart payments-worker?",
    "Can you explain how to patch the redis.maxmemory-policy config?",
]

WRITES = [
    ("restart checkout-api now", WriteActionType.RESTART_SERVICE, "checkout-api"),
    ("Restart checkout-api now!", WriteActionType.RESTART_SERVICE, "checkout-api"),
    ("Please restart the checkout-api service now", WriteActionType.RESTART_SERVICE, "checkout-api"),
    ("Quick one: restart payments-worker", WriteActionType.RESTART_SERVICE, "payments-worker"),
    ("Hey, when you get a chance, page the oncall for the payments outage",
     WriteActionType.PAGE_ONCALL, "payments outage"),
    ("I need you to patch the redis.maxmemory-policy config to allkeys-lru",
     WriteActionType.PATCH_CONFIG, "redis.maxmemory-policy"),
]


@pytest.mark.parametrize("query", READS)
def test_informational_cue_anywhere_is_not_a_write(query: str) -> None:
    assert detect_write_intent(query) is None


@pytest.mark.parametrize(("query", "action", "target"), WRITES)
def test_imperatives_still_propose(query: str, action: WriteActionType, target: str) -> None:
    w = detect_write_intent(query)
    assert w is not None
    assert w.action_type is action
    assert w.target == target
    assert w.query == query.strip()  # raw query kept for the audit trail


def test_inflections_and_descriptions_do_not_become_writes() -> None:
    assert detect_write_intent("checkout-api restarts every night") is None
    assert detect_write_intent("payments-worker was patched yesterday") is None


def test_quick_question_how_do_i_restart_is_not_propose_write(copilot: Copilot) -> None:
    result = copilot.ask("Quick question: how do I restart checkout-api")
    assert result.decision is not Decision.PROPOSE_WRITE
    assert result.proposed_write is None
    result = copilot.ask("Quick question: how do I restart the checkout-api service?")
    assert result.decision is Decision.REFUSE_UNGROUNDED  # same label as the clean g45


def test_restart_now_still_proposes_write() -> None:
    bot = Copilot()
    result = bot.ask("restart checkout-api now")
    assert result.decision is Decision.PROPOSE_WRITE
    assert result.proposed_write is not None
    assert result.proposed_write["executed"] is False


# g42: the page-oncall cue used to be anchored to the end of the query, so a
# shuffled or trailing clause dropped the write.
@pytest.mark.parametrize(
    ("query", "target"),
    [
        ("Page the oncall the for outage payments", "outage payments"),
        ("Page the oncall for the payments outage", "payments outage"),
        ("Page the on-call for payments now", "payments"),
        ("Payments is down, page the on-call", "primary"),
        ("page the oncall, checkout is erroring", "primary"),
    ],
)
def test_page_oncall_is_position_independent(query: str, target: str) -> None:
    w = detect_write_intent(query)
    assert w is not None and w.action_type is WriteActionType.PAGE_ONCALL
    assert w.target == target


def test_page_oncall_reads_stay_reads() -> None:
    assert detect_write_intent("What is the page oncall procedure?") is None
    assert detect_write_intent("How do I page the oncall for payments?") is None
    assert detect_write_intent("Who gets paged by the oncall rotation?") is None


def test_g42_word_order_row_proposes_the_page(copilot: Copilot) -> None:
    result = copilot.ask("Page the oncall the for outage payments")
    assert result.decision is Decision.PROPOSE_WRITE
    assert result.proposed_write["status"] == "PENDING"
    assert result.proposed_write["proposal"]["action_type"] == "page_oncall"
    assert result.proposed_write["executed"] is False


def test_typod_question_word_keeps_how_to_a_read() -> None:
    assert detect_write_intent("Hwo do I restart checkout-api?") is None
    assert detect_write_intent("Wat is the procedure to restart checkout-api") is None
    assert detect_write_intent("restart checkout-api now") is not None
