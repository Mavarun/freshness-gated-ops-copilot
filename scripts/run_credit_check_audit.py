#!/usr/bin/env python3
"""Post-hoc audit of the shipped credited-word check -> artifacts/credit_check_audit.{json,md}."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ops_copilot.credit_check_audit import run  # noqa: E402


def main() -> int:
    out = run()
    art = ROOT / "artifacts"
    (art / "credit_check_audit.json").write_text(json.dumps(out, indent=1, sort_keys=True) + "\n")
    lines = ["# What the shipped credited-word check vetoes (post-hoc, `credit_check_audit.py`)", "",
             f"Rows: {out['n_rows']} (calibration, dev7 confirm, traps v1-v3, fresh). Rows with a veto: "
             f"{out['n_vetoed_rows']}. Effect vs the pre-change default: {out['by_effect']}.", "",
             "Credited stop words: " + ", ".join(f"`{w}` {n}" for w, n in out["credited_words"].items()) + ".", "",
             "| row | set | expected | check off -> on | effect | vetoed credit |",
             "| :--- | :--- | :--- | :--- | :--- | :--- |"]
    for v in sorted(out["vetoes"], key=lambda v: (v["effect"], v["id"])):
        lines.append(f"| {v['id']} | {v['set']} | {v['expect']} | {v['pre']} -> {v['now']} | {v['effect']} | "
                     f"{'; '.join(v['credits'])} |")
    lines.append("")
    (art / "credit_check_audit.md").write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
