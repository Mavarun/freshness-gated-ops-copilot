"""Numbers in the README's Nov 25 credential-request section match the committed artifacts."""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
C = json.loads((ROOT / "artifacts" / "credential_request_confirm.json").read_text())
A = json.loads((ROOT / "artifacts" / "credential_advice.json").read_text())
HEAD = "## Credential requests (2026-11-25)"
TEXT = (ROOT / "README.md").read_text(encoding="utf-8")


def _section() -> str:
    start = TEXT.index(HEAD)
    return TEXT[start: TEXT.index("\n## ", start + 5)]


def test_newest_first():
    heads = [h for h in TEXT.splitlines() if h.startswith("## ")]
    assert heads[0].startswith(HEAD) and heads[1].startswith("## Credential-request gate (2026-11-24, second slice)")
    assert f"gate off answers {len(C['part_a']['request_answered_off'])} of 16 requests" in heads[0]
    w = A["results"]["wide"]["coverage"]
    assert (f"ships `{A['pick']}` ({w['nov25_confirm']['advised']} / {w['nov25_confirm']['eligible']} and "
            f"{w['nov24_fresh']['advised']} / {w['nov24_fresh']['eligible']} covered") in heads[0]


def test_confirm_claims():
    s = _section()
    req = [r for r in C["confirm"] if r["kind"] == "request"]
    assert "**Gate off answers 0 of 16 requests**" in s and C["part_a"]["gate_stays_on"]
    assert sum(r["on"] == "REFUSE_UNGROUNDED" for r in req) == 12 and "(12 ungrounded," in s
    assert not C["part_b"]["ships"] and len(C["part_b"]["regression_changed"]) == 0
    assert "0 of 751 regression rows and 0 of 24 legit rows change" in s
    assert "the shipped rule flags 1 of 8 state-word requests, the extension 8 of 8" in s


def test_advice_table():
    s = _section()
    for arm, label in (("wide", "`wide` (rule + imperative)"), ("shipped", "`shipped` (rule only)")):
        r = A["results"][arm]
        cov = r["coverage"]
        row = (f"| {label} | {len(r['changed'])} | {len(r['legit_advised'])} | {len(r['regression_advised'])} | "
               f"{cov['nov25_confirm']['advised']} / {cov['nov25_confirm']['eligible']} | "
               f"{cov['nov24_fresh']['advised']} / {cov['nov24_fresh']['eligible']} | {r['passes']} |")
        assert row in s, row
    assert A["results"]["wide"]["regression_advised"] == ["d8-t07"] and "`d8-t07`" in s
