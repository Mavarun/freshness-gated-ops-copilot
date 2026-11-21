#!/usr/bin/env python3
"""Run the pre-registered contact-channel rule -> artifacts/contact_channel.{json,md}.

Scores the 751 Nov 20 rows (dev10 excluded) and the 19-row fresh confirm set with
``pii_contact_auth`` = "phrases" and "channel" on top of the shipped default, then applies
contact_channel_protocol.checks().
"""

from __future__ import annotations

import json
import sys
from dataclasses import replace
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from ops_copilot import contact_channel_protocol as P  # noqa: E402
from ops_copilot.config import CopilotConfig  # noqa: E402
from ops_copilot.pipeline import Copilot  # noqa: E402
from run_hazard_scan_protocol import rows as nov20_rows  # noqa: E402

ART = ROOT / "artifacts"


def confirm_rows() -> list[dict]:
    return [json.loads(x) for x in (ROOT / P.CONFIRM_FILE).read_text().splitlines() if x.strip()]


def _advice(res) -> list[str]:
    return [x["action"] for x in (res.explanation or {}).get("remediation", [])]


def score(phrases: Copilot, channel: Copilot, rs: list[dict]) -> list[dict]:
    out = []
    for r in rs:
        a, b = phrases.ask(r["query"]), channel.ask(r["query"])
        out.append({
            "id": r["id"], "query": r["query"], "expect": r["expect_decision"],
            "phrases": a.decision.value, "channel": b.decision.value,
            "phrases_advice": _advice(a), "channel_advice": _advice(b),
        })
    return out


def summary(rs: list[dict]) -> dict:
    return {
        "n": len(rs),
        "correct": {arm: sum(r[arm] == r["expect"] for r in rs) for arm in ("phrases", "channel")},
        "misfires": {arm: sum(P.is_misfire(r["expect"], r[arm]) for r in rs) for arm in ("phrases", "channel")},
        "answered": {arm: sum(r[arm] == "ANSWER" for r in rs) for arm in ("phrases", "channel")},
    }


def run() -> dict:
    base = CopilotConfig()
    phrases = Copilot(config=replace(base, pii_contact_auth="phrases"))
    channel = Copilot(config=replace(base, pii_contact_auth="channel"))
    a = score(phrases, channel, nov20_rows())
    b = score(phrases, channel, confirm_rows())
    return {
        "regression": {**summary(a), "changed": [r for r in a if r["phrases"] != r["channel"]]},
        "confirm": {**summary(b), "rows": b},
        "checks": P.checks(a, b),
    }


def render(out: dict) -> str:
    A, B = out["regression"], out["confirm"]
    lines = [
        "# Contact-channel authorization (2026-11-21)",
        "",
        f"Rule: `contact_channel_protocol.py`, written before this run. Regression rows: {A['n']} (dev10 not read); "
        f"confirm rows: {B['n']}.",
        "",
        "| set | correct phrases -> channel | hazard misfires phrases -> channel | answered phrases -> channel |",
        "| :--- | ---: | ---: | ---: |",
    ]
    for name, s in (("regression", A), ("confirm", B)):
        lines.append(
            f"| {name} | {s['correct']['phrases']} -> {s['correct']['channel']} | "
            f"{s['misfires']['phrases']} -> {s['misfires']['channel']} | "
            f"{s['answered']['phrases']} -> {s['answered']['channel']} |"
        )
    lines += ["", "## Regression rows that changed", "",
              "| id | query | label | phrases | channel | advice phrases -> channel |",
              "| :--- | :--- | :--- | :--- | :--- | :--- |"]
    for r in A["changed"]:
        lines.append(f"| `{r['id']}` | {r['query']} | {r['expect']} | {r['phrases']} | {r['channel']} | "
                     f"{', '.join(r['phrases_advice'])} -> {', '.join(r['channel_advice'])} |")
    lines += ["", "## Confirm set", "", "| id | query | label | phrases | channel |", "| :--- | :--- | :--- | :--- | :--- |"]
    for r in B["rows"]:
        lines.append(f"| `{r['id']}` | {r['query']} | {r['expect']} | {r['phrases']} | {r['channel']} |")
    ch = out["checks"]
    lines += ["", "| check | result |", "| :--- | :--- |",
              *[f"| {k} | {'pass' if v else 'FAIL'} |" for k, v in ch.items() if k != "ship"],
              "", f"**Decision: {'ships on' if ch['ship'] else 'stays off'}.**", ""]
    return "\n".join(lines)


def main() -> int:
    out = run()
    ART.mkdir(exist_ok=True)
    (ART / "contact_channel.json").write_text(json.dumps(out, indent=2) + "\n")
    (ART / "contact_channel.md").write_text(render(out))
    print(render(out))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
