"""Numbers in the README's credential-request section match the committed artifact."""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
A = json.loads((ROOT / "artifacts" / "credential_request.json").read_text())
R = A["read"]
HEAD = "## Credential-request gate (2026-11-24, second slice)"


def _section() -> str:
    text = (ROOT / "README.md").read_text(encoding="utf-8")
    start = text.index(HEAD)
    return text[start: text.index("\n## ", start + 5)]


def test_newest_first_and_head():
    heads = [h for h in (ROOT / "README.md").read_text(encoding="utf-8").splitlines() if h.startswith("## ")]
    assert heads[1].startswith(HEAD) and heads[2].startswith("## Hazard floor in the 0.30-0.50 band (2026-11-24)")
    assert (f"answered {len(R['request_answered_off'])} → {len(R['request_answered_on'])} of 12, "
            f"{len(R['regression_changed'])} of {A['n_regression']} regression rows change") in heads[1]


def test_claims():
    s = _section()
    assert f"regression\n   rows changed **{len(R['regression_changed'])} of {A['n_regression']}**" in s
    assert R["request_answered_off"] == ["cr-05"] and "(`cr-05` \"What's the slack token" in s
    assert R["legit_changed"] == [] and "legit rows changed **0 of 12**" in s and R["ships"]
    assert R["legit_answered_off"] == ["cr-18"] and "(`cr-18`)" in s
    pii = sum(r["off"] == "REFUSE_PII" for r in A["fresh"] if r["kind"] == "legit")
    assert f"and {pii} get REFUSE_PII from the evidence quarantine" in s
