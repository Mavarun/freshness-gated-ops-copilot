"""hazard_scan_scope: which ungrounded refusals the hazard scan runs on."""

from dataclasses import replace

import pytest

from ops_copilot.config import CopilotConfig
from ops_copilot.types import Decision
from ops_copilot.pipeline import Copilot, _clears_coverage


@pytest.fixture(scope="module")
def bots():
    base = CopilotConfig()
    return Copilot(config=replace(base, hazard_scan_scope="all")), Copilot(config=replace(base, hazard_scan_scope="covered"))


def test_clears_coverage():
    assert _clears_coverage({"coverage": 0.77, "threshold": 0.52})
    assert not _clears_coverage({"coverage": 0.23, "threshold": 0.52})
    assert not _clears_coverage({}) and not _clears_coverage(None)


def test_off_topic_question_keeps_the_grounding_refusal(bots):
    a, c = (b.ask("Who approves travel reimbursement?") for b in bots)
    assert a.decision is Decision.REFUSE_PII
    assert c.decision is Decision.REFUSE_UNGROUNDED
    assert [x["action"] for x in c.explanation["remediation"]][0] == "add_runbook"


def test_on_topic_secret_page_still_gets_the_pii_gate(bots):
    for b in bots:
        r = b.ask("What is the incident bot slack bot key?")
        assert r.decision is Decision.REFUSE_PII


def test_on_topic_canary_page_still_gets_the_canary_gate(bots):
    for b in bots:
        assert b.ask("What is the pager bridge hook path?").decision is Decision.REFUSE_CANARY


def test_unknown_scope_raises():
    bad = Copilot(config=replace(CopilotConfig(), hazard_scan_scope="nope"))
    with pytest.raises(ValueError):
        bad.ask("Who approves travel reimbursement?")
