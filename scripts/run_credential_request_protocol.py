#!/usr/bin/env python3
"""Run the pre-registered credential-request protocol -> artifacts/credential_request.{json,md}.

Scores the 751 regression rows and the 24-row fresh set with the shipped default (gate off) and
with ``credential_request_gate=True``, and applies credential_request_protocol.read().
"""

from __future__ import annotations

import json
import sys
from dataclasses import replace
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from ops_copilot import credential_request_protocol as P  # noqa: E402
from ops_copilot.config import CopilotConfig  # noqa: E402
from ops_copilot.pipeline import Copilot  # noqa: E402
from run_hazard_scan_protocol import rows as regression_rows  # noqa: E402

ART = ROOT / "artifacts"


def fresh_rows() -> list[dict]:
    return [json.loads(x) for x in (ROOT / P.FRESH_FILE).read_text().splitlines() if x.strip()]


def score() -> tuple[list[dict], list[dict]]:
    base = CopilotConfig(credential_request_gate=False)
    off, on = Copilot(config=base), Copilot(config=replace(base, credential_request_gate=True))
    reg = []
    for r in regression_rows():
        a, b = off.ask(r["query"]).decision.value, on.ask(r["query"]).decision.value
        reg.append({"id": r["id"], "expect": r["expect_decision"], "off": a, "on": b})
    fresh = []
    for r in fresh_rows():
        fresh.append({"id": r["id"], "kind": r["kind"], "query": r["query"],
                      "off": off.ask(r["query"]).decision.value, "on": on.ask(r["query"]).decision.value})
    return reg, fresh


def render(reg: list[dict], fresh: list[dict], res: dict) -> str:
    lines = ["# Credential-request gate (2026-11-24)", "",
             "Rule: `credential_request_protocol.py`, written before the gate was coded.", "",
             f"Regression rows: {len(reg)}; changed: {len(res['regression_changed'])} "
             f"({', '.join(res['regression_changed']) or 'none'}); ANSWER-labelled changed: "
             f"{len(res['regression_answer_changed'])}.", "",
             "| id | kind | query | gate off | gate on |", "| :--- | :--- | :--- | :--- | :--- |"]
    for r in fresh:
        lines.append(f"| `{r['id']}` | {r['kind']} | {r['query']} | {r['off']} | {r['on']} |")
    c = res["checks"]
    lines += ["", f"Request rows answered: gate off {len(res['request_answered_off'])} / 12, gate on "
              f"{len(res['request_answered_on'])} / 12. Legit rows changed: {len(res['legit_changed'])} / 12 "
              f"(answered with gate off: {len(res['legit_answered_off'])}).", "",
              f"Checks: regression_safe={c['regression_safe']}, requests_refused={c['requests_refused']}, "
              f"legit_unchanged={c['legit_unchanged']}.", "", f"**Ships: {res['ships']}.**", ""]
    return "\n".join(lines)


def main() -> int:
    reg, fresh = score()
    res = P.read(reg, fresh)
    ART.mkdir(exist_ok=True)
    changed = [r for r in reg if r["off"] != r["on"]]
    (ART / "credential_request.json").write_text(json.dumps(
        {"n_regression": len(reg), "regression_changed_rows": changed, "fresh": fresh, "read": res}, indent=2) + "\n")
    md = render(reg, fresh, res)
    (ART / "credential_request.md").write_text(md)
    print(md)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
