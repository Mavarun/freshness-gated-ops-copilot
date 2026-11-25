#!/usr/bin/env python3
"""Run the pre-registered credential-advice protocol -> artifacts/credential_advice.{json,md}.

Arms: ``credential_request_advice`` = off (base), ``shipped`` and ``wide``, on the 751 regression rows,
the Nov 25 confirm set and the Nov 24 fresh set; applies credential_advice_protocol.read_arm().
"""

from __future__ import annotations

import json
import sys
from dataclasses import replace
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from ops_copilot import credential_advice_protocol as P  # noqa: E402
from ops_copilot import credential_request_confirm_protocol as C  # noqa: E402
from ops_copilot.config import CopilotConfig  # noqa: E402
from ops_copilot.pipeline import Copilot  # noqa: E402
from run_hazard_scan_protocol import rows as regression_rows  # noqa: E402

ART = ROOT / "artifacts"


def _load(name: str) -> list[dict]:
    return [json.loads(x) for x in (ROOT / name).read_text().splitlines() if x.strip()]


def _advised(res) -> bool:
    e = res.explanation or {}
    return bool((e.get("details") or {}).get("credential_request"))


def score():
    base = CopilotConfig(credential_request_advice="off")
    arms = {"base": Copilot(config=base),
            **{a: Copilot(config=replace(base, credential_request_advice=a)) for a in P.ARMS}}

    def run(q: str) -> dict:
        out = {}
        for k, c in arms.items():
            r = c.ask(q)
            out[k] = r.decision.value
            if k != "base":
                out[f"adv_{k}"] = _advised(r)
        return out

    reg = [{"id": r["id"], "expect": r["expect_decision"], **run(r["query"])} for r in regression_rows()]
    fresh = {name: [{"id": r["id"], "kind": r["kind"], "query": r["query"], **run(r["query"])} for r in _load(f)]
             for name, f in (("nov25_confirm", C.CONFIRM_FILE), ("nov24_fresh", C.NOV24_FILE))}
    return reg, fresh


def render(results: dict, pick: str | None) -> str:
    lines = ["# Credential-request advice (2026-11-25)", "",
             "Rules: `credential_advice_protocol.py`, written before the advice was coded.", "",
             "| arm | decisions changed | ANSWER rows advised | legit advised | regression advised | "
             "Nov 25 coverage | Nov 24 coverage | passes |",
             "| :--- | ---: | ---: | ---: | ---: | ---: | ---: | :--- |"]
    for arm in P.ARMS:
        r = results[arm]
        cov = r["coverage"]
        lines.append(f"| `{arm}` | {len(r['changed'])} | {len(r['answer_advised'])} | {len(r['legit_advised'])} | "
                     f"{len(r['regression_advised'])} | {cov['nov25_confirm']['advised']} / "
                     f"{cov['nov25_confirm']['eligible']} | {cov['nov24_fresh']['advised']} / "
                     f"{cov['nov24_fresh']['eligible']} | {r['passes']} |")
    lines += [""]
    for arm in P.ARMS:
        r = results[arm]
        lines.append(f"- `{arm}`: missed Nov 25 {', '.join(r['coverage']['nov25_confirm']['missed']) or 'none'}; "
                     f"missed Nov 24 {', '.join(r['coverage']['nov24_fresh']['missed']) or 'none'}; "
                     f"regression rows advised: {', '.join(r['regression_advised']) or 'none'}.")
    lines += ["", f"**Ships: `{pick or 'off'}`.**", ""]
    return "\n".join(lines)


def main() -> int:
    reg, fresh = score()
    results = {arm: P.read_arm(reg, fresh, arm) for arm in P.ARMS}
    pick = P.pick(results)
    advised_rows = [r for r in reg if any(r[f"adv_{a}"] for a in P.ARMS)]
    ART.mkdir(exist_ok=True)
    (ART / "credential_advice.json").write_text(json.dumps(
        {"n_regression": len(reg), "regression_advised_rows": advised_rows, "fresh": fresh,
         "results": results, "pick": pick}, indent=2) + "\n")
    md = render(results, pick)
    (ART / "credential_advice.md").write_text(md)
    print(md)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
