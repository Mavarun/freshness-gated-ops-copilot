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


# --- secrets disclosed in words (no recognisable shape) ---------------------------

from ops_copilot.explain_redact import (  # noqa: E402
    DISCLOSED_SECRET_RE,
    PR15_PATTERNS,
    redact_explanation as _rx,
    redact_string as _rs,
)


@pytest.mark.parametrize(
    "text, value",
    [
        ("My password is violet harbor zebra, why can't I log in?", "violet harbor zebra"),
        ("The vault passphrase is quokka plinth. Who owns it?", "quokka plinth"),
        ("restart checkout-api, the admin pin is 4471 mango", "4471 mango"),
        ("Token was blue quokka yesterday; what is the TTL?", "blue quokka yesterday"),
        ("the db credentials are saffron and who owns them", "saffron"),
        ("secret: violet harbor", "violet harbor"),
    ],
)
def test_disclosed_secret_value_is_found_and_redacted(text: str, value: str) -> None:
    m = DISCLOSED_SECRET_RE.search(text)
    assert m is not None and m.group("val") == value
    out, n = _rs(text, context=[text])
    assert n >= 1 and value not in out and "[redacted:disclosed_secret]" in out
    again, n2 = _rs(out, context=[text])
    assert again == out and n2 == 0  # idempotent


@pytest.mark.parametrize(
    "text",
    [
        "the password is in vault",
        "What is the password rotation policy?",
        "Is the token TTL 24h?",
        "What is the auth secret TTL?",
        "Who owns the api key for checkout?",
        "When was the password changed",
    ],
)
def test_ordinary_credential_questions_are_left_alone(text: str) -> None:
    assert DISCLOSED_SECRET_RE.search(text) is None
    assert _rs(text, context=[text]) == (text, 0)


def test_only_the_value_is_fragmented_not_the_cue_word() -> None:
    q = "Token was blue quokka yesterday; what is the auth token TTL?"
    expl, n = _rx({"missing_terms": ["quokka", "token", "blue", "ttl"]}, context=[q])
    assert expl["missing_terms"] == ["[redacted]", "token", "[redacted]", "ttl"] and n == 2


def test_pr15_pattern_set_is_the_old_one() -> None:
    assert "disclosed_secret" not in {k for k, _ in PR15_PATTERNS}


def test_disclosure_eval_pins_before_after_and_no_over_redaction() -> None:
    import json
    from pathlib import Path

    art = json.loads(
        (Path(__file__).resolve().parents[1] / "artifacts" / "explanation_eval.json").read_text()
    )
    for run in art.values():
        d = run["disclosure"]
        assert d["rows"] == 35 and d["n_words_total"] == 70
        assert d["raw_words"] == 70 and d["pr15_words"] == 65 and d["now_words"] == 0
        assert d["over_redacted_queries"] == {"golden": 0, "perturbed": 0, "write": 0}


RANDOM = "q7xf2lpz9mkw3tvb"  # synthetic, no format


@pytest.mark.parametrize(
    "query",
    [
        f"Why does {RANDOM} get a 401 from checkout-api?",
        f"use {RANDOM} to log in to vault",
        f"restart checkout-api with {RANDOM}",
    ],
)
def test_random_token_with_no_cue_is_redacted(copilot: Copilot, query: str) -> None:
    res = copilot.ask(query)
    assert RANDOM in res.as_dict()["query"].lower()  # in-process keeps raw text
    safe = res.boundary_dict()
    blob = json.dumps({k: safe.get(k) for k in (*BOUNDARY_FIELDS, "explanation")}).lower()
    assert RANDOM not in blob
    assert "[redacted:random_token]" in safe["query"]


def test_random_token_detector_keeps_write_ids_and_targets(copilot: Copilot) -> None:
    res = copilot.ask("Please restart the checkout-api service now")
    raw, safe = res.as_dict(), res.boundary_dict()
    assert safe["proposed_write"] == raw["proposed_write"]  # write id + timestamps intact


def test_random_token_hit_inside_a_shaped_secret_is_not_double_counted() -> None:
    from ops_copilot.explain_redact import find_sensitive

    kinds = [k for k, _ in find_sensitive("why did CNRY-VAULT7F3A leak")]
    assert kinds == ["canary"]


def test_pr16_pattern_set_has_no_random_token_detector() -> None:
    from ops_copilot.explain_redact import PR16_PATTERNS, SENSITIVE_PATTERNS

    assert [k for k, _ in SENSITIVE_PATTERNS][-1] == "random_token"
    assert "random_token" not in {k for k, _ in PR16_PATTERNS}
    assert "random_token" not in {k for k, _ in PR15_PATTERNS}


def test_random_token_eval_pins_before_after_and_no_over_redaction() -> None:
    from pathlib import Path

    art = json.loads(
        (Path(__file__).resolve().parents[1] / "artifacts" / "explanation_eval.json").read_text()
    )
    for run in art.values():
        rt = run["random_tokens"]
        assert rt["total"]["rows"] == 105
        assert rt["total"]["raw"] == rt["total"]["pr16"] == 105
        assert rt["gated_now"] == 0
        assert rt["by_family"]["pronounceable"]["now"] == rt["total"]["now"]  # only the known hard case leaks
        assert rt["over_redacted_queries"] == {"golden": 0, "perturbed": 0, "write": 0}
