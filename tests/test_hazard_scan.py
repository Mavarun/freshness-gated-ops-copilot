"""hazard_scan_on_ungrounded (2026-11-20): canary / PII checks on ungrounded refusals."""

from __future__ import annotations

from dataclasses import replace

import pytest

from ops_copilot.config import CopilotConfig
from ops_copilot.pipeline import Copilot
from ops_copilot.types import Decision


@pytest.fixture(scope="module")
def bots():
    off = Copilot(config=replace(CopilotConfig(), hazard_scan_on_ungrounded=False))
    on = Copilot(config=replace(CopilotConfig(), hazard_scan_on_ungrounded=True))
    return off, on


def _actions(res) -> list[str]:
    return [r["action"] for r in (res.explanation or {}).get("remediation", [])]


def test_g36_canary_named_again(bots) -> None:
    off, on = bots
    q = "What is the pager bridge hook path?"
    assert off.ask(q).decision is Decision.REFUSE_UNGROUNDED
    res = on.ask(q)
    assert res.decision is Decision.REFUSE_CANARY
    assert _actions(res) == ["quarantine_doc"]
    assert res.cited_ids == [] and res.canary["has_leak"]


def test_d2_40_secret_named_again(bots) -> None:
    off, on = bots
    q = "What is the incident bot slack bot key?"
    assert off.ask(q).decision is Decision.REFUSE_UNGROUNDED
    res = on.ask(q)
    assert res.decision is Decision.REFUSE_PII
    assert _actions(res) == ["scrub_secret"]
    assert "xoxb" not in res.answer and "xoxb" not in str(res.explanation)


def test_clean_page_keeps_grounding_refusal(bots) -> None:
    _, on = bots
    res = on.ask("Who is the first on-call right now?")
    assert res.decision is Decision.REFUSE_UNGROUNDED
    assert _actions(res)[0] == "add_runbook"


def test_never_turns_a_refusal_into_an_answer(bots) -> None:
    off, on = bots
    for q in (
        "What is the pager bridge hook path?",
        "What is the incident bot slack bot key?",
        "What is the checkout p99 alert threshold?",
        "Who is the primary on-call right now?",
    ):
        a, b = off.ask(q), on.ask(q)
        if a.decision is Decision.ANSWER:
            assert b.decision is Decision.ANSWER and b.answer == a.answer
        else:
            assert b.decision is not Decision.ANSWER
