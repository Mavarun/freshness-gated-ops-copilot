"""API contract tests via FastAPI TestClient — no live server required."""

from __future__ import annotations

from fastapi.testclient import TestClient

from ops_copilot.api import _copilot_for_clock, create_app
from ops_copilot.types import Decision


client = TestClient(create_app())


def setup_function() -> None:
    _copilot_for_clock.cache_clear()


def test_health_ok() -> None:
    resp = client.get("/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert "2026-09-13" in body["clock"]
    assert body["corpus_docs"] >= 20
    assert body["use_source_slas"] is True


def test_sources_sla_table() -> None:
    resp = client.get("/sources")
    assert resp.status_code == 200
    body = resp.json()
    assert body["global_default_hours"] == 48
    assert body["sources"]["grafana"] == 1
    assert body["sources"]["confluence"] == 168
    assert body["use_source_slas"] is True


def test_query_happy_path_answer() -> None:
    resp = client.post(
        "/query",
        json={"query": "What is the current checkout p99 latency?"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["decision"] == Decision.ANSWER.value
    assert "2410" in body["answer_or_refusal"] or "latency" in body["answer_or_refusal"].lower()
    assert isinstance(body["evidence"], list) and len(body["evidence"]) >= 1
    assert isinstance(body["ages"], list) and len(body["ages"]) == len(body["evidence"])
    assert "trace_id" in body and len(body["trace_id"]) > 8
    assert body["latency_ms"] >= 0
    assert body["sla_used"]["mode"] == "per_source"
    assert "reason" in body


def test_query_refuse_stale() -> None:
    resp = client.post(
        "/query",
        json={"query": "What is the Redis maxmemory-policy?"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["decision"] == Decision.REFUSE_STALE.value
    assert "stale" in body["answer_or_refusal"].lower() or "REFUSE" in body["answer_or_refusal"]
    assert body["ages"]
    assert max(body["ages"]) > 48
    assert body["trace_id"]
    assert body["cited_ids"] == []


def test_query_refuse_stale_grafana_sla() -> None:
    """Per-source grafana 1h SLA refuses a ~2.5h live scrape under EVAL_CLOCK."""
    resp = client.post(
        "/query",
        json={"query": "What is the live payments-api request rate?"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["decision"] == Decision.REFUSE_STALE.value
    sla = body["sla_used"]["per_source"]
    assert "grafana" in sla
    assert sla["grafana"] == 1.0


def test_query_empty_rejected() -> None:
    resp = client.post("/query", json={"query": "   "})
    assert resp.status_code == 422


def test_query_optional_clock_override() -> None:
    # Far-future clock makes everything look ancient → still structured refuse/answer.
    resp = client.post(
        "/query",
        json={
            "query": "What is the current checkout p99 latency?",
            "clock": "2099-01-01T00:00:00+00:00",
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["decision"] in {d.value for d in Decision}
    assert body["trace_id"]
    # Ages should be huge relative to 2099.
    assert body["ages"] and min(body["ages"]) > 1000


def test_query_refuse_disagree() -> None:
    resp = client.post(
        "/query",
        json={"query": "What is the sidecar mesh mtls handshake budget?"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["decision"] == Decision.REFUSE_DISAGREE.value
    assert body["disagreement"] is not None
    assert body["disagreement"]["agreed"] is False
    assert body["cited_ids"] == []
