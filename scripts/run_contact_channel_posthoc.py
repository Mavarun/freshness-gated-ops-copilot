#!/usr/bin/env python3
"""Post-hoc reading of the contact-channel confirm set -> artifacts/contact_channel_posthoc.{json,md}.

Selects nothing and changes no default. For every confirm row that is wrong under the
shipped "channel" arm, or whose decision the arm changed, it records which page each arm's
explanation names, the missing terms, and the advice. Question: are the remaining misses a
PII-gate problem or a grounding problem, and was the f-cc12 PII refusal under "phrases"
about the right page?
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from ops_copilot.config import CopilotConfig, pre_contact_config  # noqa: E402
from ops_copilot.pipeline import Copilot  # noqa: E402
from run_contact_channel_protocol import confirm_rows  # noqa: E402

ART = ROOT / "artifacts"


def _view(res) -> dict:
    e = res.explanation or {}
    return {
        "decision": res.decision.value,
        "evidence": list(e.get("evidence_doc_ids") or res.cited_ids or []),
        "missing": list(e.get("missing_terms") or []),
        "advice": [x["action"] for x in e.get("remediation", [])],
    }


def run() -> dict:
    bots = {"phrases": Copilot(config=pre_contact_config()), "channel": Copilot(config=CopilotConfig())}
    rows = []
    for r in confirm_rows():
        v = {arm: _view(b.ask(r["query"])) for arm, b in bots.items()}
        if v["channel"]["decision"] != r["expect_decision"] or v["channel"]["decision"] != v["phrases"]["decision"]:
            rows.append({"id": r["id"], "query": r["query"], "expect": r["expect_decision"], **v})
    wrong = [x for x in rows if x["channel"]["decision"] != x["expect"]]
    return {
        "rows": rows,
        "wrong_under_channel": [x["id"] for x in wrong],
        "wrong_by_gate": {
            "grounding": sum(x["channel"]["decision"] == "REFUSE_UNGROUNDED" for x in wrong),
            "pii": sum(x["channel"]["decision"] == "REFUSE_PII" for x in wrong),
        },
        "pii_refusal_on_contact_page_for_owner_question": [
            x["id"] for x in rows
            if x["expect"] == "REFUSE_PII" and x["phrases"]["decision"] == "REFUSE_PII"
            and x["phrases"]["evidence"] == ["pii_vault_transit_rotation_contact"]
        ],
    }


def render(out: dict) -> str:
    lines = ["# Contact-channel confirm set, post-hoc (selects nothing)", "",
             "| id | label | phrases (page; advice) | channel (page; missing; advice) |", "| :--- | :--- | :--- | :--- |"]
    for x in out["rows"]:
        p, c = x["phrases"], x["channel"]
        lines.append(f"| `{x['id']}` | {x['expect']} | {p['decision']} ({', '.join(p['evidence'])}; {', '.join(p['advice'])}) | "
                     f"{c['decision']} ({', '.join(c['evidence'])}; {', '.join(c['missing']) or '-'}; {', '.join(c['advice'])}) |")
    g = out["wrong_by_gate"]
    lines += ["", f"Wrong under channel: {len(out['wrong_under_channel'])} rows ({g['grounding']} grounding, {g['pii']} PII).",
              f"PII refusals for an owner question that named the contact page under phrases: "
              f"{', '.join(out['pii_refusal_on_contact_page_for_owner_question']) or 'none'}.", ""]
    return "\n".join(lines)


def main() -> int:
    out = run()
    (ART / "contact_channel_posthoc.json").write_text(json.dumps(out, indent=2) + "\n")
    (ART / "contact_channel_posthoc.md").write_text(render(out))
    print(render(out))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
