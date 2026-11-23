"""hazard_scan_scope="floor": the hazard scan runs only when the closest page reaches a fixed coverage."""

from dataclasses import replace

import pytest

from ops_copilot.config import CopilotConfig
from ops_copilot.pipeline import Copilot, _clears_coverage
from ops_copilot.types import Decision


@pytest.fixture(scope="module")
def floor_bot():
    return Copilot(config=replace(CopilotConfig(), hazard_scan_scope="floor"))


def test_default_ships_floor_at_the_nov20_candidate_and_records_keep_all():
    from ops_copilot.config import pre_contact_config, pre_floor_config

    cfg = CopilotConfig()
    assert cfg.hazard_scan_scope == "floor" and cfg.hazard_scan_floor == 0.30  # hazard_floor.json: ship
    assert pre_floor_config().hazard_scan_scope == "all" == pre_contact_config().hazard_scan_scope
    assert pre_floor_config().pii_contact_auth == cfg.pii_contact_auth == "channel"


def test_shipped_default_keeps_the_grounding_refusal_off_topic():
    r = Copilot().ask("Who approves travel reimbursement?")
    assert r.decision is Decision.REFUSE_UNGROUNDED


def test_clears_coverage_with_a_floor():
    assert _clears_coverage({"coverage": 0.36, "threshold": 0.52}, floor=0.30)
    assert not _clears_coverage({"coverage": 0.36, "threshold": 0.52})
    assert not _clears_coverage({"coverage": 0.246, "threshold": 0.52}, floor=0.30)
    assert _clears_coverage({"coverage": 0.30, "threshold": 0.52}, floor=0.30)
    assert not _clears_coverage({}, floor=0.0) and not _clears_coverage(None, floor=0.0)


def test_off_topic_question_keeps_the_grounding_refusal(floor_bot):
    r = floor_bot.ask("Who approves travel reimbursement?")
    assert r.decision is Decision.REFUSE_UNGROUNDED
    assert [x["action"] for x in r.explanation["remediation"]][0] == "add_runbook"


def test_on_topic_hazard_pages_keep_their_gates(floor_bot):
    assert floor_bot.ask("What is the incident bot slack bot key?").decision is Decision.REFUSE_PII
    assert floor_bot.ask("What is the pager bridge hook path?").decision is Decision.REFUSE_CANARY


def test_floor_zero_scans_every_refusal_with_a_coverage_figure():
    b = Copilot(config=replace(CopilotConfig(), hazard_scan_scope="floor", hazard_scan_floor=0.0))
    assert b.ask("Who approves travel reimbursement?").decision is Decision.REFUSE_PII
