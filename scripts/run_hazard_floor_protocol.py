#!/usr/bin/env python3
"""Run the pre-registered hazard-floor rule -> artifacts/hazard_floor.{json,md}.

Scores the 751 regression rows (dev10 excluded) and the 28-row fresh confirm set with
``hazard_scan_scope`` "all" (shipped) and "floor" (0.30) and applies
hazard_floor_protocol.ships(). Also records, per changed or misfiring row, the closest
page's coverage read with the scan off (descriptive only).
"""

from __future__ import annotations

import json
import sys
from dataclasses import replace
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from ops_copilot import hazard_floor_protocol as P  # noqa: E402
from ops_copilot.config import ADVICE_OFF, HAZARD_OFF, CopilotConfig  # noqa: E402
from ops_copilot.pipeline import Copilot  # noqa: E402
from run_hazard_scan_protocol import rows as regression_rows  # noqa: E402

ART = ROOT / "artifacts"


def _advice(r) -> list[str]:
    return [x["action"] for x in (r.explanation or {}).get("remediation", [])]


def _coverage(bot: Copilot, q: str):
    d = (bot.ask(q).explanation or {}).get("details") or {}
    c = d.get("coverage")
    return round(float(c), 3) if c is not None else None


def score(bot_all: Copilot, bot_floor: Copilot, scan_off: Copilot, rs: list[dict]) -> dict:
    scored, notable = [], []
    for r in rs:
        a, f = bot_all.ask(r["query"]), bot_floor.ask(r["query"])
        row = {"id": r["id"], "expect": r["expect_decision"], "all": a.decision.value, "floor": f.decision.value}
        scored.append(row)
        if a.decision != f.decision or P.is_misfire(row["expect"], row["all"]) or P.is_misfire(row["expect"], row["floor"]):
            notable.append({**row, "query": r["query"], "advice_all": _advice(a), "advice_floor": _advice(f),
                            "coverage": _coverage(scan_off, r["query"])})
    return {"n_rows": len(scored), "rows": scored, "notable": notable}


def confirm_rows() -> list[dict]:
    return [json.loads(x) for x in (ROOT / P.CONFIRM_FILE).read_text().splitlines() if x.strip()]


def render(out: dict) -> str:
    lines = [f"# Hazard scan floor {P.FLOOR}: 'all' vs 'floor' (2026-11-23)", "",
             "Rule: `hazard_floor_protocol.py`, written before this run. dev10 not read.", ""]
    for part in ("regression", "confirm"):
        res, ch = out[part], out["decision"][part]
        lines += [f"## {part} ({res['n_rows']} rows)", "",
                  "| id | query | label | all | floor | coverage | advice all -> floor |",
                  "| :--- | :--- | :--- | :--- | :--- | ---: | :--- |"]
        for c in res["notable"]:
            lines.append(f"| `{c['id']}` | {c['query']} | {c['expect']} | {c['all']} | {c['floor']} | {c['coverage']} | "
                         f"{', '.join(c['advice_all'])} -> {', '.join(c['advice_floor'])} |")
        lines += ["", f"Hazard misfires: all {ch['misfires_all']}, floor {ch['misfires_floor']}; "
                  f"labelled canary/PII rows lost: {ch['lost_fixes']}; answer changes: {ch['answer_changes']}.", "",
                  "| check | result |", "| :--- | :--- |",
                  *[f"| {k} | {'pass' if ch[k] else 'FAIL'} |" for k in ("no_answer_change", "keeps_fixes", "misfires_ok")], ""]
    band = out["confirm"]["must_refuse_scan_off"]
    via = [b for b in band if b["scan_off"] == "REFUSE_UNGROUNDED"]
    lines += [f"Confirm must-refuse rows that reach their gate only through the ungrounded scan: {len(via)} of {len(band)}, "
              "closest-page coverage " + ", ".join(f"`{b['id']}` {b['coverage']}" for b in via) + " (descriptive).", ""]
    lines += [f"**Decision: {'floor ships' if out['decision']['ship'] else 'all stays'}.**", ""]
    return "\n".join(lines)


def main() -> int:
    base = replace(CopilotConfig(), **ADVICE_OFF)  # scored before the Nov 25 advice shipped
    bots = (Copilot(config=replace(base, hazard_scan_scope="all")),
            Copilot(config=replace(base, hazard_scan_scope="floor", hazard_scan_floor=P.FLOOR)),
            Copilot(config=replace(base, **HAZARD_OFF)))
    reg, con = score(*bots, regression_rows()), score(*bots, confirm_rows())
    # descriptive: which confirm must-refuse rows reach their gate only through the ungrounded
    # scan (scan off -> REFUSE_UNGROUNDED), and the coverage of their closest page
    band = []
    for r in confirm_rows():
        if r["kind"] == "must_refuse":
            off = bots[2].ask(r["query"])
            band.append({"id": r["id"], "scan_off": off.decision.value, "coverage": _coverage(bots[2], r["query"])})
    con["must_refuse_scan_off"] = band
    out = {"floor": P.FLOOR, "regression": reg, "confirm": con, "decision": P.ships(reg["rows"], con["rows"])}
    ART.mkdir(exist_ok=True)
    (ART / "hazard_floor.json").write_text(json.dumps(out, indent=2) + "\n")
    (ART / "hazard_floor.md").write_text(render(out))
    print(render(out))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
