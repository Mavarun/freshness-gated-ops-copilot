#!/usr/bin/env python3
"""Run the pre-registered hazard-scan rule -> artifacts/hazard_scan.{json,md}.

Scores every committed labelled row (dev10 excluded) with ``hazard_scan_on_ungrounded``
off and on, on top of the shipped default, and applies hazard_scan_protocol.ships().
"""

from __future__ import annotations

import json
import sys
from collections import Counter
from dataclasses import replace
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ops_copilot import hazard_scan_protocol as P  # noqa: E402
from ops_copilot.config import CopilotConfig  # noqa: E402
from ops_copilot.paraphrase_set import load_paraphrase_set  # noqa: E402
from ops_copilot.pipeline import Copilot  # noqa: E402

ART = ROOT / "artifacts"


def rows() -> list[dict]:
    golden = [json.loads(x) for x in (ROOT / "data/golden/questions.jsonl").read_text().splitlines() if x.strip()]
    out = [dict(r, id=f"golden-{i:02d}") for i, r in enumerate(golden)]
    for rel in P.EVAL_FILES:
        assert rel not in P.UNSEEN
        out += [json.loads(x) for x in (ROOT / rel).read_text().splitlines() if x.strip()]
    out += [dict(r, id=str(r["id"])) for r in load_paraphrase_set()]
    assert len({r["id"] for r in out}) == len(out), "duplicate row ids"
    return out


def score(knob_off: Copilot, knob_on: Copilot, rs: list[dict]) -> dict:
    changed, gates = [], Counter()
    for r in rs:
        a, b = knob_off.ask(r["query"]), knob_on.ask(r["query"])
        gates[a.decision.value] += 1
        if a.decision != b.decision:
            changed.append({
                "id": r["id"], "query": r["query"], "expect": r["expect_decision"],
                "off": a.decision.value, "on": b.decision.value,
                "off_remediation": [x["action"] for x in (a.explanation or {}).get("remediation", [])],
                "on_remediation": [x["action"] for x in (b.explanation or {}).get("remediation", [])],
                "effect": P.classify(r["expect_decision"], a.decision.value, b.decision.value),
            })
    effects = dict(Counter(c["effect"] for c in changed))
    return {"n_rows": len(rs), "off_decisions": dict(gates), "changed": changed,
            "effects": effects, "checks": P.ships(effects)}


def render(out: dict) -> str:
    lines = [
        "# Hazard scan on ungrounded refusals (2026-11-20)",
        "",
        f"Rows scored: {out['n_rows']} (dev10 not read). Rule: `hazard_scan_protocol.py`, written before this run.",
        "",
        "| id | query | label | knob off | knob on | advice off -> on | effect |",
        "| :--- | :--- | :--- | :--- | :--- | :--- | :--- |",
    ]
    for c in out["changed"]:
        lines.append(
            f"| `{c['id']}` | {c['query']} | {c['expect']} | {c['off']} | {c['on']} | "
            f"{', '.join(c['off_remediation'])} -> {', '.join(c['on_remediation'])} | {c['effect']} |"
        )
    ch = out["checks"]
    lines += [
        "",
        "| check | result |",
        "| :--- | :--- |",
        *[f"| {k} | {'pass' if v else 'FAIL'} |" for k, v in ch.items() if k != "ship"],
        "",
        f"**Decision: {'ships on' if ch['ship'] else 'stays off'}.**",
        "",
    ]
    return "\n".join(lines)


def main() -> int:
    base = CopilotConfig()
    off = Copilot(config=replace(base, hazard_scan_on_ungrounded=False))
    on = Copilot(config=replace(base, hazard_scan_on_ungrounded=True))
    out = score(off, on, rows())
    ART.mkdir(exist_ok=True)
    (ART / "hazard_scan.json").write_text(json.dumps(out, indent=2) + "\n")
    (ART / "hazard_scan.md").write_text(render(out))
    print(render(out))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
