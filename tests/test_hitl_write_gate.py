"""HITL write gate: propose stays PENDING; approve executes stub; reject never executes."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from ops_copilot import Copilot, CopilotConfig
from ops_copilot.api import _copilot_for_clock, create_app, get_copilot
from ops_copilot.hitl import HitlWriteLedger, WriteStatus
from ops_copilot.types import Decision
from ops_copilot.write_actions import WriteActionType, detect_write_intent


def test_detect_restart_page_patch() -> None:
    r = detect_write_intent("Please restart the checkout-api service now")
    assert r is not None
    assert r.action_type is WriteActionType.RESTART_SERVICE
    assert r.target == "checkout-api"

    p = detect_write_intent("Page the oncall for the payments outage")
    assert p is not None
    assert p.action_type is WriteActionType.PAGE_ONCALL

    c = detect_write_intent(
        "Please patch the redis.maxmemory-policy config to allkeys-lru"
    )
    assert c is not None
    assert c.action_type is WriteActionType.PATCH_CONFIG
    assert c.payload.get("value") == "allkeys-lru"


def test_how_to_read_does_not_propose() -> None:
    assert detect_write_intent("How do I restart the checkout-api service?") is None
    assert detect_write_intent("What is the current checkout p99 latency?") is None


def test_pipeline_propose_write_pending() -> None:
    bot = Copilot(config=CopilotConfig())
    result = bot.ask("Please restart the checkout-api service now")
    assert result.decision is Decision.PROPOSE_WRITE
    assert result.proposed_write is not None
    assert result.proposed_write["status"] == WriteStatus.PENDING.value
    assert result.proposed_write["executed"] is False
    wid = result.proposed_write["write_id"]
    pending = bot.hitl.list_pending()
    assert any(r.write_id == wid for r in pending)


def test_approve_executes_stub_once() -> None:
    ledger = HitlWriteLedger()
    bot = Copilot(config=CopilotConfig(), hitl=ledger)
    result = bot.ask("Can you restart payments-worker?")
    wid = result.proposed_write["write_id"]
    approved = ledger.approve(wid, actor="oncall-lead")
    assert approved.status is WriteStatus.EXECUTED
    assert approved.executed is True
    assert approved.execution_result is not None
    assert approved.execution_result["stub"] is True
    events = [a.event for a in approved.audit]
    assert events == ["propose", "approve", "execute_stub"]


def test_reject_never_executes() -> None:
    ledger = HitlWriteLedger()
    bot = Copilot(config=CopilotConfig(), hitl=ledger)
    result = bot.ask("Page the oncall for the checkout latency spike")
    wid = result.proposed_write["write_id"]
    rejected = ledger.reject(wid, actor="sre-manager", reason="false alarm")
    assert rejected.status is WriteStatus.REJECTED
    assert rejected.executed is False
    assert rejected.execution_result is None
    with pytest.raises(PermissionError):
        ledger.execute_stub(wid, actor="rogue")
    with pytest.raises(ValueError):
        ledger.approve(wid, actor="someone")


def test_execute_stub_blocked_while_pending() -> None:
    ledger = HitlWriteLedger()
    bot = Copilot(config=CopilotConfig(), hitl=ledger)
    result = bot.ask("Please patch nginx.worker_connections config to 4096")
    wid = result.proposed_write["write_id"]
    with pytest.raises(PermissionError, match="PENDING"):
        ledger.execute_stub(wid)


def test_read_path_answer_unchanged() -> None:
    bot = Copilot(config=CopilotConfig())
    result = bot.ask("What is the current checkout p99 latency?")
    assert result.decision is Decision.ANSWER
    assert result.proposed_write is None


def test_hitl_gate_can_disable() -> None:
    bot = Copilot(config=CopilotConfig(use_hitl_write_gate=False))
    # Without HITL, restart query falls through normal evidence gates.
    result = bot.ask("Please restart the checkout-api service now")
    assert result.decision is not Decision.PROPOSE_WRITE


client = TestClient(create_app())


def setup_function() -> None:
    _copilot_for_clock.cache_clear()


def test_api_propose_then_approve() -> None:
    resp = client.post(
        "/query",
        json={"query": "Please restart the checkout-api service now"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["decision"] == Decision.PROPOSE_WRITE.value
    assert body["proposed_write"] is not None
    assert body["proposed_write"]["status"] == "PENDING"
    wid = body["proposed_write"]["write_id"]

    appr = client.post(
        f"/writes/{wid}/approve",
        json={"actor": "alice"},
    )
    assert appr.status_code == 200
    rec = appr.json()
    assert rec["status"] == "EXECUTED"
    assert rec["executed"] is True
    assert rec["execution_result"]["stub"] is True


def test_api_propose_then_reject_blocks_execute() -> None:
    resp = client.post(
        "/query",
        json={"query": "Page the oncall for the payments outage"},
    )
    assert resp.status_code == 200
    wid = resp.json()["proposed_write"]["write_id"]

    rej = client.post(
        f"/writes/{wid}/reject",
        json={"actor": "bob", "reason": "noise"},
    )
    assert rej.status_code == 200
    rec = rej.json()
    assert rec["status"] == "REJECTED"
    assert rec["executed"] is False

    # Approve after reject must conflict
    bad = client.post(f"/writes/{wid}/approve", json={"actor": "bob"})
    assert bad.status_code == 409


def test_api_pending_list() -> None:
    get_copilot(None).hitl.reset()
    client.post("/query", json={"query": "Can you restart payments-worker?"})
    pending = client.get("/writes/pending")
    assert pending.status_code == 200
    rows = pending.json()
    assert len(rows) >= 1
    assert all(r["status"] == "PENDING" for r in rows)


def test_api_unknown_write_404() -> None:
    resp = client.post(
        "/writes/wrt_does_not_exist/approve",
        json={"actor": "alice"},
    )
    assert resp.status_code == 404
