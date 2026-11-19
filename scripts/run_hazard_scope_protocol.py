#!/usr/bin/env python3
"""Run the pre-registered hazard-scope rule -> artifacts/hazard_scope.{json,md}.

Scores every committed labelled row (dev10 excluded) with ``hazard_scan_scope`` "all" and
"covered" on top of the shipped default and applies hazard_scope_protocol.ships().
"""

from __future__ import annotations

import json
import sys
from dataclasses import replace
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from ops_copilot import hazard_scope_protocol as P  # noqa: E402
from ops_copilot.config import CopilotConfig  # noqa: E402
from ops_copilot.pipeline import Copilot  # noqa: E402
from run_hazard_scan_protocol import rows  # noqa: E402

ART = ROOT / "artifacts"


def _advice(r) -> list[str]:
    return [x["action"] for x in (r.explanation or {}).get("remediation", [])]


def score(bot_all: Copilot, bot_cov: Copilot, rs: list[dict]) -> dict:
    scored, changed = [], []
    for r in rs:
        a, c = bot_all.ask(r["query"]), bot_cov.ask(r["query"])
        row = {"id": r["id"], "expect": r["expect_decision"], "all": a.decision.value, "covered": c.decision.value}
        scored.append(row)
        if a.decision != c.decision:
            changed.append({**row, "query": r["query"], "advice_all": _advice(a), "advice_covered": _advice(c)})
    misfires = [s for s in scored if P.is_misfire(s["expect"], s["covered"])]
    return {"n_rows": len(scored), "changed": changed, "checks": P.ships(scored),
            "remaining_misfires": [{"id": m["id"], "expect": m["expect"], "decision": m["covered"]} for m in misfires]}


def render(out: dict) -> str:
    ch = out["checks"]
    lines = ["# Hazard scan scope: 'all' vs 'covered' (2026-11-20)", "",
             f"Rows scored: {out['n_rows']} (dev10 not read). Rule: `hazard_scope_protocol.py`, written before this run.", "",
             "| id | query | label | all | covered | advice all -> covered |", "| :--- | :--- | :--- | :--- | :--- | :--- |"]
    for c in out["changed"]:
        lines.append(f"| `{c['id']}` | {c['query']} | {c['expect']} | {c['all']} | {c['covered']} | "
                     f"{', '.join(c['advice_all'])} -> {', '.join(c['advice_covered'])} |")
    lines += ["", f"Hazard misfires (canary/PII refusal on a row labelled neither): all {ch['misfires_all']}, "
              f"covered {ch['misfires_covered']}; labelled canary/PII rows lost: {ch['lost_fixes']}; "
              f"answer changes: {ch['answer_changes']}.", "",
              "| check | result |", "| :--- | :--- |",
              *[f"| {k} | {'pass' if ch[k] else 'FAIL'} |" for k in ("no_answer_change", "keeps_fixes", "fewer_hazard_misfires")],
              "", "Misfires left under 'covered': " + (", ".join(f"`{m['id']}` ({m['expect']} -> {m['decision']})"
                                                         for m in out["remaining_misfires"]) or "none") + ".",
              "", f"**Decision: {'covered ships' if ch['ship'] else 'all stays'}.**", ""]
    return "\n".join(lines)


def main() -> int:
    base = CopilotConfig()
    out = score(Copilot(config=replace(base, hazard_scan_scope="all")),
                Copilot(config=replace(base, hazard_scan_scope="covered")), rows())
    ART.mkdir(exist_ok=True)
    (ART / "hazard_scope.json").write_text(json.dumps(out, indent=2) + "\n")
    (ART / "hazard_scope.md").write_text(render(out))
    print(render(out))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
