"""The credential-request protocol's reading rule and its fresh set, fixed before any run."""

import json
from pathlib import Path

from ops_copilot import credential_request_protocol as P

ROOT = Path(__file__).resolve().parents[1]


def _fresh():
    return [json.loads(x) for x in (ROOT / P.FRESH_FILE).read_text().splitlines() if x.strip()]


def test_fresh_set_shape():
    rows = _fresh()
    assert len(rows) == 24 and len({r["id"] for r in rows}) == 24
    assert sum(r["kind"] == "request" for r in rows) == 12 and sum(r["kind"] == "legit" for r in rows) == 12


def test_fresh_rows_are_not_regression_rows():
    import sys
    sys.path.insert(0, str(ROOT / "scripts"))
    from run_hazard_scan_protocol import rows
    reg = {r["query"].lower() for r in rows()}
    clash = [r["id"] for r in _fresh() if r["query"].lower() in reg]
    assert clash == ["cr-14"]  # the golden-10 question, kept on purpose as a must-not-change control


def _reg(i, expect, off, on):
    return {"id": i, "expect": expect, "off": off, "on": on}


def _fr(i, kind, off, on):
    return {"id": i, "kind": kind, "off": off, "on": on}


def test_pass():
    r = P.read([_reg("a", "ANSWER", "ANSWER", "ANSWER"), _reg("b", "REFUSE_PII", "ANSWER", "REFUSE_PII")],
               [_fr("x", "request", "ANSWER", "REFUSE_PII"), _fr("y", "legit", "ANSWER", "ANSWER")])
    assert r["ships"] and r["request_answered_off"] == ["x"] and r["regression_changed"] == ["b"]


def test_each_failure():
    assert not P.read([_reg("a", "ANSWER", "ANSWER", "REFUSE_PII")], [])["checks"]["regression_safe"]
    two = [_reg("a", "REFUSE_PII", "ANSWER", "REFUSE_PII"), _reg("b", "REFUSE_PII", "ANSWER", "REFUSE_PII")]
    assert not P.read(two, [])["checks"]["regression_safe"]
    assert not P.read([], [_fr("x", "request", "ANSWER", "ANSWER")])["checks"]["requests_refused"]
    assert not P.read([], [_fr("y", "legit", "ANSWER", "REFUSE_PII")])["checks"]["legit_unchanged"]
