#!/usr/bin/env python3
"""Safety sweep of the dev3-chosen Datamuse arm -> artifacts/datamuse_dev3_safety_sweep.{json,md}.

Runs the shipped default and the dev3-chosen arm on every query literal in
tests/ and lists each changed decision (``ops_copilot.safety_sweep``). Exits 0;
the ship decision it records is: off if any labelled trap opens.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ops_copilot.datamuse_dev3 import config_for  # noqa: E402
from ops_copilot.safety_sweep import sweep  # noqa: E402


def main() -> int:
    art = ROOT / "artifacts"
    chosen = json.loads((art / "datamuse_dev3_confirm.json").read_text())["chosen"]
    rep = {"chosen": chosen, **sweep(config_for(chosen))}
    rep["ships"] = "on" if rep["safe"] else "off (a labelled unit-test trap opens)"
    (art / "datamuse_dev3_safety_sweep.json").write_text(json.dumps(rep, indent=2, sort_keys=True) + "\n")
    lines = ["# dev3-chosen Datamuse arm: changed decisions on every unit-test query literal", "",
             f"Arm: {chosen}. Queries: {rep['n_queries']}; changed: {len(rep['changed'])}; "
             f"refusal -> ANSWER/PROPOSE_WRITE: {rep['n_opened']}; labelled traps opened: "
             f"{len(rep['labelled_trap_opened'])}. Ships: **{rep['ships']}**.", "",
             "| query | default | arm | opened | expected (asserted in) |", "| --- | --- | --- | :---: | --- |"]
    for c in rep["changed"]:
        exp = f"{c['expected']} ({c['asserted_in']})" if c["expected"] else "unlabelled"
        lines.append(f"| {c['query']} | {c['base']} | {c['candidate']} | {'yes' if c['opened'] else '-'} | {exp} |")
    (art / "datamuse_dev3_safety_sweep.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
