"""pii_contact_auth knob (2026-11-21): 'phrases' (old allowlist) vs 'channel'."""

from __future__ import annotations

from dataclasses import replace

import pytest

from ops_copilot.config import CopilotConfig
from ops_copilot.pii_redact import scan_answer_pii
from ops_copilot.pipeline import Copilot
from ops_copilot.types import Decision

CONTACT_DRAFT = "The vault-transit key rotation contact email is ops-secrets@example.com."


@pytest.fixture(scope="module")
def bots():
    base = CopilotConfig()
    return (
        Copilot(config=replace(base, pii_contact_auth="phrases")),
        Copilot(config=replace(base, pii_contact_auth="channel")),
    )


def test_scan_channel_mode_widens_only_with_designation() -> None:
    q = "What is the vault-transit key rotation contact inbox?"
    assert scan_answer_pii(CONTACT_DRAFT, q).action == "refuse"
    ch = scan_answer_pii(CONTACT_DRAFT, q, contact_auth="channel")
    assert ch.action == "redact" and ch.authorized
    assert "ops-secrets@example.com" not in ch.redacted_text
    owner = "The directory lists ops-secrets@example.com as the primary owner mailbox for break-glass."
    assert scan_answer_pii(owner, "What is the owner mailbox?", contact_auth="channel").action == "refuse"


def test_scan_channel_mode_keeps_old_phrases_and_refuses_secrets() -> None:
    q = "What is the vault-transit key rotation contact email?"
    assert scan_answer_pii(CONTACT_DRAFT, q, contact_auth="channel").action == "redact"
    s = scan_answer_pii("The pager contact key is AKIATESTKEY000000000.", "pager contact email?", contact_auth="channel")
    assert s.action == "refuse" and s.has_secret


def test_unknown_mode_raises() -> None:
    with pytest.raises(ValueError):
        scan_answer_pii(CONTACT_DRAFT, "contact email", contact_auth="fuzzy")


def test_default_is_phrases_until_the_protocol_runs() -> None:
    assert CopilotConfig().pii_contact_auth == "phrases"


def test_contact_inbox_answers_masked_under_channel(bots) -> None:
    phrases, channel = bots
    q = "What is the vault-transit key rotation contact inbox?"
    assert phrases.ask(q).decision is Decision.REFUSE_PII
    res = channel.ask(q)
    assert res.decision is Decision.ANSWER
    assert "ops-secrets@example.com" not in res.answer and "o***@example.com" in res.answer


def test_liaison_email_gets_grounding_refusal_not_pii(bots) -> None:
    phrases, channel = bots
    q = "What is the vault-transit key rotation liaison email?"
    assert phrases.ask(q).decision is Decision.REFUSE_PII
    res = channel.ask(q)
    assert res.decision is Decision.REFUSE_UNGROUNDED
    assert "scrub_secret" not in [r["action"] for r in res.explanation["remediation"]]


def test_owner_pages_stay_refused_under_channel(bots) -> None:
    _, channel = bots
    for q in ("What is the vault-transit rotation owner directory?", "What is the vault-transit rotation owner mailbox?"):
        assert channel.ask(q).decision is Decision.REFUSE_PII, q
