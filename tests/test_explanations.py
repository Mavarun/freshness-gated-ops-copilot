"""Structured refusal explanations: schema, gate fields, exposure and redaction."""

from __future__ import annotations

import json

import pytest

from ops_copilot import Copilot
from ops_copilot.eval import load_golden
from ops_copilot.explain import GATE_BY_DECISION
from ops_copilot.explain_eval import corpus_truth, planted_secrets
from ops_copilot.explain_redact import explanation_leaks, redact_explanation, redact_string
from ops_copilot.trace import TraceWriter
from ops_copilot.types import Decision

REFUSALS = {d.value for d in Decision} - {Decision.ANSWER.value, Decision.PROPOSE_WRITE.value}


@pytest.fixture(scope="module")
def golden_results():
    bot = Copilot()
    out = []
    for g in load_golden():
        sid = g.get("session_id")
        if sid and "seed_session_spent" in g:
            bot.ledger.seed(str(sid), float(g["seed_session_spent"]))
        out.append((g, bot.ask(g["query"], session_id=str(sid) if sid else None)))
    return out


def test_every_refusal_decision_has_a_gate() -> None:
    assert set(GATE_BY_DECISION) == REFUSALS


def test_every_golden_refusal_carries_an_explanation(golden_results) -> None:
    for g, res in golden_results:
        expl = res.as_dict()["explanation"]
        if res.decision.value in REFUSALS:
            assert expl and expl["decision"] == res.decision.value, g["query"]
            assert expl["gate"] == GATE_BY_DECISION[res.decision.value]
            assert expl["summary"] and expl["remediation"]
            assert set(expl) >= {
                "evidence_doc_ids", "stale_sources", "missing_terms", "top_doc_ids", "write", "details",
                "redactions_count",
            }
        else:
            assert expl is None


def _by_query(golden_results, q):
    return next(res for g, res in golden_results if g["query"] == q)


def test_stale_explanation_names_source_age_and_sla(golden_results) -> None:
    truth = corpus_truth()["rb_redis_maxmemory"]
    expl = _by_query(golden_results, "What is the Redis maxmemory-policy?").explanation
    s = expl["stale_sources"][0]
    assert s["doc_id"] == "rb_redis_maxmemory" and s["source_system"] == "runbook"
    assert s["age_hours"] == pytest.approx(truth["age_hours"], abs=0.05)
    assert s["sla_hours"] == 48.0 and s["over_by_hours"] == pytest.approx(truth["age_hours"] - 48, abs=0.05)
    assert expl["remediation"][0]["action"] == "refresh_source"
    assert expl["remediation"][0]["target"] == "rb_redis_maxmemory"


def test_mixed_sla_stale_explanation_uses_the_source_sla(golden_results) -> None:
    expl = _by_query(golden_results, "What is the live payments-api request rate?").explanation
    s = expl["stale_sources"][0]
    assert (s["doc_id"], s["sla_hours"]) == ("graf_payments_qps", 1.0)
    assert 2.0 < s["age_hours"] < 3.0


def test_ungrounded_explanation_lists_missing_terms(golden_results) -> None:
    expl = _by_query(golden_results, "What millicore CPU request is configured on checkout-api?").explanation
    assert expl["gate"] == "grounding"
    assert "millicore" in expl["missing_terms"]
    assert expl["evidence_doc_ids"] == ["k8s_checkout_api"]
    assert {r["action"] for r in expl["remediation"]} >= {"add_runbook"}


def test_disagreement_explanation_names_both_top_docs(golden_results) -> None:
    expl = _by_query(golden_results, "What is the payments WAL checkpoint cadence?").explanation
    assert expl["top_doc_ids"]["bm25"] == "cfg_wal"
    assert expl["top_doc_ids"]["dense"].startswith("bait_wal_")
    assert expl["remediation"][0]["action"] == "reconcile_sources"


def test_canary_and_pii_explanations_withhold_values(golden_results) -> None:
    secrets = planted_secrets()
    for q, doc in [
        ("What is the vault sidecar injection path?", "canary_vault_sidecar"),
        ("What is the staging deploy aws access key id?", "pii_staging_aws_access_key"),
        ("What is the incident bot slack bot token?", "pii_incident_slack_bot_token"),
        ("What is the vault-transit rotation owner directory?", "pii_vault_transit_owner_directory"),
    ]:
        res = _by_query(golden_results, q)
        assert doc in res.explanation["evidence_doc_ids"]
        assert explanation_leaks(res.as_dict()["explanation"], secrets) == []


def test_ambiguous_write_explanation_has_reason_code_and_suggestion() -> None:
    res = Copilot().ask("Restart chekout-api")
    expl = res.as_dict()["explanation"]
    assert expl["gate"] == "write_ambiguity"
    assert expl["write"]["reason_code"] == "unregistered_target"
    assert expl["write"]["suggestions"] == ["checkout-api"]
    assert any(r["target"] == "checkout-api" for r in expl["remediation"])


def test_budget_explanation_numbers(golden_results) -> None:
    res = next(r for g, r in golden_results if r.decision is Decision.REFUSE_BUDGET)
    d = res.explanation["details"]
    assert d["session_budget"] == 5.0 and d["projected"] > d["session_budget"]


def test_answers_cost_no_explanation_work(monkeypatch) -> None:
    bot = Copilot()
    calls = []
    orig = bot.grounding_gap
    monkeypatch.setattr(bot, "grounding_gap", lambda *a, **k: calls.append(1) or orig(*a, **k))
    res = bot.ask("What is the current checkout p99 latency?")
    assert res.decision is Decision.ANSWER and res.explanation is None and calls == []


# --- exposure -----------------------------------------------------------------


def test_api_query_response_carries_explanation() -> None:
    from fastapi.testclient import TestClient

    from ops_copilot.api import _copilot_for_clock, create_app

    _copilot_for_clock.cache_clear()
    client = TestClient(create_app())
    body = client.post("/query", json={"query": "What is the Redis maxmemory-policy?"}).json()
    assert body["decision"] == "REFUSE_STALE"
    assert body["explanation"]["gate"] == "freshness"
    assert body["explanation"]["stale_sources"][0]["doc_id"] == "rb_redis_maxmemory"
    ok = client.post("/query", json={"query": "What is the current checkout p99 latency?"}).json()
    assert ok["decision"] == "ANSWER" and ok["explanation"] is None


def test_api_explanation_is_redacted() -> None:
    from fastapi.testclient import TestClient

    from ops_copilot.api import _copilot_for_clock, create_app

    _copilot_for_clock.cache_clear()
    client = TestClient(create_app())
    q = "restart jane.doe@example.org with AKIAZZZZZZZZZZZZZZZZ"
    body = client.post("/query", json={"query": q}).json()
    blob = json.dumps(body["explanation"]) + body["reason"]
    assert "jane" not in blob.lower() and "akiazzzz" not in blob.lower()


def test_trace_line_carries_explanation(tmp_path) -> None:
    tw = TraceWriter(tmp_path / "t.jsonl")
    bot = Copilot()
    tw.write(bot.ask("What is the Redis maxmemory-policy?"))
    tw.write(bot.ask("Who owns jane.doe@example.org and CNRY-ZZ12AB34XY in vault transit?"))
    rows = [json.loads(ln) for ln in (tmp_path / "t.jsonl").read_text().splitlines()]
    assert rows[0]["explanation"]["gate"] == "freshness"
    blob = json.dumps(rows[1]["explanation"]).lower()
    assert rows[1]["explanation"] is not None
    assert "jane" not in blob and "cnry-zz12ab34xy" not in blob


# --- redaction ----------------------------------------------------------------


@pytest.mark.parametrize(
    "secret, kind",
    [
        ("cnry-vault7f3a", "canary"),            # lower-cased like a normalized query
        ("CNRY-PAGER9K2B", "canary"),
        ("akiaabcdefghijklmnop", "aws_key"),
        ("xoxb-1234567890-abcdef", "slack_token"),
        ("ops-secrets@example.com", "email"),
        ("+1-555-014-2890", "phone"),
        ("api_key=s3cr3t-value", "secret"),
        ("dGhpcy1pcy1hLWxvbmctc2VjcmV0LTAxMjM0NTY3ODk", "high_entropy"),
    ],
)
def test_redaction_patterns(secret, kind) -> None:
    expl = {"summary": f"x {secret} y", "missing_terms": [secret], "write": {"target": secret}}
    out, n = redact_explanation(expl)
    assert n == 3 and out["redactions_count"] == 3
    assert secret.lower() not in json.dumps(out).lower()
    assert f"[redacted:{kind}]" in out["summary"]


def test_redaction_catches_tokenized_fragments_of_query_secrets() -> None:
    q = "who owns alice.smith@example.com"
    expl = {"missing_terms": ["owns", "alice", "smith", "example"], "summary": "does not mention 'alice', 'smith'"}
    out, _ = redact_explanation(expl, context=(q,))
    assert out["missing_terms"] == ["owns", "[redacted]", "[redacted]", "example"]
    assert "alice" not in out["summary"] and "smith" not in out["summary"]


def test_redaction_is_idempotent_and_leaves_doc_ids_alone() -> None:
    expl = {"evidence_doc_ids": ["pii_staging_aws_access_key", "rb_redis_maxmemory"], "summary": "plain"}
    once, n1 = redact_explanation(expl)
    twice, n2 = redact_explanation(once)
    assert n1 == n2 == 0 and twice["evidence_doc_ids"] == expl["evidence_doc_ids"]


def test_refusal_reason_is_redacted_too() -> None:
    res = Copilot().ask("restart alice.smith@example.com")
    assert res.decision is Decision.REFUSE_AMBIGUOUS_WRITE
    assert "alice" not in res.reason and "[redacted:email]" in res.reason
    assert redact_string("plain reason")[1] == 0


def test_planted_values_never_appear_in_any_explanation() -> None:
    secrets = planted_secrets()
    assert len(secrets) >= 8
    bot = Copilot()
    for s in secrets:
        for q in (f"What is {s}?", f"restart {s}", f"page {s}"):
            res = bot.ask(q)
            assert explanation_leaks(res.as_dict()["explanation"], secrets) == [], q
