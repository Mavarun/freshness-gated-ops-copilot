"""Secrets pasted into a query never reach a trace line or the API response."""

from __future__ import annotations

import json

import pytest

from ops_copilot import Copilot
from ops_copilot.explain_redact import BOUNDARY_FIELDS, boundary_leaks, redact_boundary
from ops_copilot.trace import TraceWriter, result_to_trace

AWS = "AKIA" + "Q7XK2M4P9R3T6W8Y"  # synthetic, AWS-key shaped
EMAIL = "alice.smith@example.com"
PROBES = [
    f"Restart checkout-api, my key is {AWS}",
    f"What is the checkout p99 latency? cc {EMAIL}",
    f"patch maxmemory-policy password={'hunter2' * 3}",
    "Why did CNRY-7f3a9c2e leak into the runbook?",
]


@pytest.mark.parametrize("query", PROBES)
def test_trace_line_has_no_sensitive_span(copilot: Copilot, tmp_path, query: str) -> None:
    res = copilot.ask(query)
    raw = res.as_dict()
    assert boundary_leaks(raw), "probe should leak in the raw in-process dict"
    path = tmp_path / "t.jsonl"
    TraceWriter(path).write(res)
    line = json.loads(path.read_text(encoding="utf-8").splitlines()[0])
    assert boundary_leaks(line) == []
    assert AWS.lower() not in json.dumps(line).lower()
    assert "alice" not in json.dumps({k: line[k] for k in BOUNDARY_FIELDS if k in line})
    assert line["boundary_redactions"] >= 1
    assert line["decision"] == raw["decision"]  # redaction never changes the decision


def test_clean_query_is_untouched(copilot: Copilot) -> None:
    res = copilot.ask("What is the current checkout p99 latency?")
    safe = result_to_trace(res)
    assert safe["query"] == res.query and safe["boundary_redactions"] == 0


def test_in_process_result_and_hitl_keep_the_raw_values(copilot: Copilot) -> None:
    q = f"Restart checkout-api, my key is {AWS}"
    res = copilot.ask(q)
    assert res.query == q  # raw for the caller; only boundaries redact
    assert AWS in res.as_dict()["query"]


def test_redact_boundary_is_idempotent() -> None:
    payload = {"query": f"mail {EMAIL} now", "reason": "x", "write_intent": {"target": "alice"}}
    once, n1 = redact_boundary(payload, query=payload["query"])
    twice, n2 = redact_boundary(once, query=payload["query"])
    assert n1 >= 2 and n2 == 0 and once == twice
    assert once["write_intent"]["target"] == "[redacted]"


def test_api_response_fields_are_redacted() -> None:
    pytest.importorskip("fastapi")
    from fastapi.testclient import TestClient

    from ops_copilot.api import app

    client = TestClient(app)
    body = client.post("/query", json={"query": f"Restart checkout-api, my key is {AWS}"}).json()
    blob = json.dumps({k: body.get(k) for k in ("reason", "write_intent", "proposed_write", "explanation")})
    assert AWS.lower() not in blob.lower()
