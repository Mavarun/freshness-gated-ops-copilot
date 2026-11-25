#!/usr/bin/env python3
"""Run the pre-registered Nov 25 credential-request confirm -> artifacts/credential_request_confirm.{json,md}.

Three arms: gate off, the shipped default (gate on), and shipped + ``credential_request_imperative``.
Part A reads off vs shipped on the 28-row confirm set; part B reads shipped vs extension on the 751
regression rows, the confirm set and the 12 Nov 24 legit rows.
"""

from __future__ import annotations

import json
import sys
from dataclasses import replace
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from ops_copilot import credential_request_confirm_protocol as P  # noqa: E402
from ops_copilot.config import CopilotConfig  # noqa: E402
from ops_copilot.credential_request import is_credential_request, is_imperative_credential_request  # noqa: E402
from ops_copilot.pipeline import Copilot  # noqa: E402
from run_hazard_scan_protocol import rows as regression_rows  # noqa: E402

ART = ROOT / "artifacts"


def _load(name: str) -> list[dict]:
    return [json.loads(x) for x in (ROOT / name).read_text().splitlines() if x.strip()]


def score() -> tuple[list[dict], list[dict], list[dict]]:
    shipped = CopilotConfig(credential_request_imperative=False)
    arms = {"off": Copilot(config=replace(shipped, credential_request_gate=False)),
            "on": Copilot(config=shipped),
            "ext": Copilot(config=replace(shipped, credential_request_imperative=True))}

    def run(q: str) -> dict:
        return {k: c.ask(q).decision.value for k, c in arms.items()}

    reg = [{"id": r["id"], "expect": r["expect_decision"], **run(r["query"])} for r in regression_rows()]
    conf = [{"id": r["id"], "kind": r["kind"], "form": r["form"], "query": r["query"], **run(r["query"]),
             "flag_shipped": is_credential_request(r["query"]),
             "flag_ext": is_credential_request(r["query"]) or is_imperative_credential_request(r["query"])}
            for r in _load(P.CONFIRM_FILE)]
    nov24 = [{"id": r["id"], "query": r["query"], **run(r["query"])}
             for r in _load(P.NOV24_FILE) if r["kind"] == "legit"]
    return reg, conf, nov24


def render(reg, conf, nov24, a, b) -> str:
    lines = ["# Credential-request confirm (2026-11-25)", "",
             "Rules: `credential_request_confirm_protocol.py`, written before any run.", "",
             "| id | kind | form | query | gate off | shipped | + imperative |",
             "| :--- | :--- | :--- | :--- | :--- | :--- | :--- |"]
    for r in conf:
        lines.append(f"| `{r['id']}` | {r['kind']} | {r['form']} | {r['query']} | {r['off']} | {r['on']} | {r['ext']} |")
    lines += ["", "## Part A: shipped gate", "",
              f"Requests answered: gate off {len(a['request_answered_off'])} / 16, shipped "
              f"{len(a['request_answered_on'])} / 16 ({', '.join(a['request_answered_on']) or 'none'}). "
              f"Base requests answered by shipped: {len(a['base_answered_on'])} / 8. "
              f"Legit rows changed off -> shipped: {len(a['legit_changed'])} / 12 "
              f"({', '.join(a['legit_changed']) or 'none'}).", "",
              f"Checks: base_refused={a['checks']['base_refused']}, "
              f"legit_within_budget={a['checks']['legit_within_budget']}. **Gate stays on: {a['gate_stays_on']}.**",
              "", "## Part B: imperative extension", "",
              f"Regression rows: {len(reg)}; changed: {len(b['regression_changed'])} "
              f"({', '.join(b['regression_changed']) or 'none'}); ANSWER-labelled changed: "
              f"{len(b['regression_answer_changed'])}.",
              f"Slip requests closed: {len(b['slip_closed'])} ({', '.join(b['slip_closed']) or 'none'}); "
              f"requests answered with the extension: {len(b['request_answered_ext'])} "
              f"({', '.join(b['request_answered_ext']) or 'none'}).",
              f"Legit rows changed (confirm + {len(nov24)} Nov 24): {len(b['legit_changed'])} "
              f"({', '.join(b['legit_changed']) or 'none'}).", "",
              f"Checks: regression_safe={b['checks']['regression_safe']}, "
              f"requests_refused={b['checks']['requests_refused']}, legit_unchanged={b['checks']['legit_unchanged']}.",
              "", f"**Extension ships: {b['ships']}.**", "",
              "## Post-hoc: detector coverage (selects nothing)", "",
              "Which rows each detector would flag if they reached ANSWER. Read after the run.", ""]
    for kind, form in (("request", "base"), ("request", "slip"), ("legit", None)):
        rows = [r for r in conf if r["kind"] == kind and (form is None or r["form"] == form)]
        lines.append(f"- {kind}{'/' + form if form else ''}: shipped rule flags "
                     f"{sum(r['flag_shipped'] for r in rows)} / {len(rows)}, with the extension "
                     f"{sum(r['flag_ext'] for r in rows)} / {len(rows)}.")
    req = [r for r in conf if r["kind"] == "request"]
    lines += [f"- Requests refused by the shipped default with a non-credential gate: "
              f"{sum(r['on'] not in ('ANSWER', 'REFUSE_PII') for r in req)} / {len(req)} "
              f"(their advice is that gate's, e.g. add_runbook / rephrase).", ""]
    return "\n".join(lines)


def main() -> int:
    reg, conf, nov24 = score()
    a, b = P.read_shipped(conf), P.read_extension(reg, conf, nov24)
    ART.mkdir(exist_ok=True)
    changed = [r for r in reg if len({r["off"], r["on"], r["ext"]}) > 1]
    (ART / "credential_request_confirm.json").write_text(json.dumps(
        {"n_regression": len(reg), "regression_changed_rows": changed, "confirm": conf, "nov24_legit": nov24,
         "part_a": a, "part_b": b}, indent=2) + "\n")
    md = render(reg, conf, nov24, a, b)
    (ART / "credential_request_confirm.md").write_text(md)
    print(md)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
