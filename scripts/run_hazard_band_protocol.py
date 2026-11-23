#!/usr/bin/env python3
"""Run the pre-registered hazard-band stress test -> artifacts/hazard_band.{json,md}.

Scores the 24-row fresh band set with ``hazard_scan_scope`` "all", the shipped "floor" (0.30)
and the scan off, records each row's closest-page coverage read with the scan off, and applies
hazard_band_protocol.read().
"""

from __future__ import annotations

import json
import sys
from dataclasses import replace
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ops_copilot import hazard_band_protocol as P  # noqa: E402
from ops_copilot.config import CRED_OFF, HAZARD_OFF, CopilotConfig  # noqa: E402
from ops_copilot.pipeline import Copilot  # noqa: E402

ART = ROOT / "artifacts"


def band_rows() -> list[dict]:
    return [json.loads(x) for x in (ROOT / P.BAND_FILE).read_text().splitlines() if x.strip()]


def score() -> list[dict]:
    base = replace(CopilotConfig(), **CRED_OFF)  # scored before the credential gate shipped
    bots = {"all": Copilot(config=replace(base, hazard_scan_scope="all")),
            "floor": Copilot(config=replace(base, hazard_scan_scope="floor", hazard_scan_floor=P.FLOOR)),
            "off": Copilot(config=replace(base, **HAZARD_OFF))}
    out = []
    for r in band_rows():
        dec = {a: b.ask(r["query"]) for a, b in bots.items()}
        d = (dec["off"].explanation or {}).get("details") or {}
        c = d.get("coverage")
        out.append({"id": r["id"], "kind": r["kind"], "query": r["query"], "expect": r["expect_decision"],
                    "coverage": round(float(c), 3) if c is not None else None,
                    **{a: v.decision.value for a, v in dec.items()}})
    return out


def render(rows: list[dict], res: dict) -> str:
    lines = [f"# Hazard floor {P.FLOOR} in the {P.BAND[0]:.2f}-{P.BAND[1]:.2f} band (2026-11-24)", "",
             "Rule: `hazard_band_protocol.py`, written before this run.", "",
             "| id | kind | query | label | coverage | all | floor | off |",
             "| :--- | :--- | :--- | :--- | ---: | :--- | :--- | :--- |"]
    for r in rows:
        lines.append(f"| `{r['id']}` | {r['kind']} | {r['query']} | {r['expect']} | {r['coverage']} | {r['all']} | "
                     f"{r['floor']} | {r['off']} |")
    share = res["band_misfire_share"]
    lines += ["", f"Misfires all / floor / off: {res['misfires']['all']} / {res['misfires']['floor']} / {res['misfires']['off']}; "
              f"correct: {res['correct']['all']} / {res['correct']['floor']} / {res['correct']['off']} of {len(rows)}.",
              f"Must-refuse rows lost by the floor: {len(res['lost'])} ({', '.join(res['lost']) or 'none'}).",
              f"Band off-topic rows: {len(res['band_off_topic'])}; misfiring under the floor: {len(res['band_misfires'])} "
              f"({', '.join(res['band_misfires']) or 'none'}); share "
              f"{'n/a' if share is None else f'{share:.2f}'}.",
              f"Answers: {len(res['answers'])}.", "",
              f"**Holds on must-refuse: {res['holds']}. Guards the band: {res['guards_band']}.**", ""]
    return "\n".join(lines)


def main() -> int:
    rows = score()
    res = P.read(rows)
    ART.mkdir(exist_ok=True)
    (ART / "hazard_band.json").write_text(json.dumps({"floor": P.FLOOR, "rows": rows, "read": res}, indent=2) + "\n")
    md = render(rows, res)
    (ART / "hazard_band.md").write_text(md)
    print(md)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
