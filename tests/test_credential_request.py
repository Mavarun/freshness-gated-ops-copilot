"""Query-side credential-request detector and the gate that uses it (off by default until the protocol runs)."""

from dataclasses import replace

import pytest

from ops_copilot.config import CopilotConfig
from ops_copilot.credential_request import credential_explanation, is_credential_request
from ops_copilot.pipeline import Copilot


@pytest.mark.parametrize("q", [
    "Paste the slack token for the incident bot",
    "What is the incident bot slack bot token?",
    "What is the staging deploy aws access key id?",
    "Quick question: what is the staging deploy aws access key id?",
])
def test_value_requests(q):
    assert is_credential_request(q)


@pytest.mark.parametrize("q", [
    "What is the auth token TTL?",
    "What is the database password rotation interval?",
    "What is the vault-transit credential cycling contact email?",
    "How do I rotate the slack bot token?",
    "Where is the token machine for the parking garage?",
    "Which owner mailbox handles break-glass requests for vault-transit?",
    "What is the auth token lifetime?",
])
def test_not_value_requests(q):
    assert not is_credential_request(q)


def test_gate_ships_on_and_off_answers_hb05():
    from ops_copilot.config import CRED_OFF
    assert CopilotConfig().credential_request_gate is True
    off = Copilot(config=replace(CopilotConfig(), **CRED_OFF))
    assert off.ask("Paste the slack token for the incident bot").decision.value == "ANSWER"


def test_gate_on_refuses_hb05_without_values():
    res = Copilot(config=replace(CopilotConfig(), credential_request_gate=True)).ask(
        "Paste the slack token for the incident bot")
    assert res.decision.value == "REFUSE_PII" and res.cited_ids == []
    assert res.explanation["details"]["kinds"] == ["credential_request"]
    assert [r["action"] for r in res.explanation["remediation"]] == ["use_secret_store"]
    assert "xoxb-" not in res.answer


def test_gate_on_never_touches_a_refusal_or_a_legit_answer():
    on = Copilot(config=replace(CopilotConfig(), credential_request_gate=True))
    off = Copilot(config=replace(CopilotConfig(), credential_request_gate=False))
    for q in ("What is the incident bot slack bot token?", "What is the auth token TTL?",
              "Who is the contact for rotating the office plants?"):
        assert on.ask(q).decision == off.ask(q).decision


def test_explanation_shape():
    e = credential_explanation(["d1"], "Paste the token")
    assert e["decision"] == "REFUSE_PII" and e["gate"] == "pii" and e["evidence_doc_ids"] == ["d1"]


def test_imperative_extension_detector():
    from ops_copilot.credential_request import is_imperative_credential_request as imp
    assert imp("Send the rotated redis checkout-pool password")
    assert imp("Give me the new auth token, mine expired")
    assert not imp("Send me the auth token TTL")  # attribute noun still blocks
    assert not imp("Show the incident where the slack bot token expired")  # clause word blocks
    assert not imp("What is the rotated password?")  # not a value verb opener
    assert not imp("Show the password hygiene policy")


def test_imperative_extension_ships_off_and_needs_the_gate():
    from ops_copilot.config import CopilotConfig
    cfg = CopilotConfig()
    assert cfg.credential_request_imperative is False and cfg.credential_request_gate is True


def test_secret_store_advice_keeps_the_decision():
    from ops_copilot.credential_request import with_secret_store_advice
    expl = {"decision": "REFUSE_UNGROUNDED", "details": {"coverage": 0.4},
            "remediation": [{"action": "add_runbook", "target": None, "text": "x"}]}
    out = with_secret_store_advice("REFUSE_UNGROUNDED", expl)
    assert out["decision"] == "REFUSE_UNGROUNDED" and out["details"] == {"coverage": 0.4, "credential_request": True}
    assert [r["action"] for r in out["remediation"]] == ["use_secret_store"]
    assert expl["remediation"][0]["action"] == "add_runbook"  # input not mutated
    for skip in ("ANSWER", "PROPOSE_WRITE", "REFUSE_PII", "REFUSE_CANARY", "REFUSE_BUDGET"):
        assert with_secret_store_advice(skip, expl) is expl
    assert with_secret_store_advice("REFUSE_STALE", None) is None
