#!/usr/bin/env python3
"""Post-hoc reading of the non-key confirm -> artifacts/nonkey_posthoc.{json,md}. Selects nothing."""

from __future__ import annotations

import dataclasses
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ops_copilot import nonkey_coverage_protocol as P  # noqa: E402
from ops_copilot.config import CopilotConfig  # noqa: E402
from ops_copilot.nonkey_posthoc import read_lost, read_trap  # noqa: E402
from ops_copilot.pipeline import Copilot  # noqa: E402
from ops_copilot.swap_null import file_rows  # noqa: E402

ART = ROOT / "artifacts"


def main() -> int:
    cal = json.loads((ART / "nonkey_calibration.json").read_text(encoding="utf-8"))
    rec = json.loads((ART / "nonkey_confirm.json").read_text(encoding="utf-8"))
    name = rec["arm"]
    ship, arm = Copilot(), Copilot(config=dataclasses.replace(CopilotConfig(), **P.ARMS[name]))
    lost = [dict(read_lost(ship, arm, r["id"], r["query"]), phase="calibration") for r in cal["lost_rows"][name]]
    lost += [dict(read_lost(ship, arm, r["id"], r["query"]), phase="confirm") for r in rec["lost_rows"]]
    dev8 = {r.id: r.query for r in file_rows((P.DEV8_FILE,))}
    traps = [read_trap(ship, arm, i, dev8[i]) for i in rec["topic_trap_opens"]["shipped"]]
    n_compound = sum(bool(r["compound_part"]) for r in lost)
    out = {"arm": name, "lost": lost, "lost_compound_part": n_compound, "traps": traps}
    (ART / "nonkey_posthoc.json").write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8")
    md = ["# Non-key coverage rule, post-hoc reading (selects nothing; the confirm call stands)", "",
          f"## Answered rows `{name}` loses ({len(lost)}; {n_compound} are a hyphen part of a cited token)", "",
          "| phase | row | query | missing word | compound part of evidence |", "| :--- | :--- | :--- | :--- | :--- |",
          *[f"| {r['phase']} | {r['id']} | {r['query']} | {', '.join(r['words'])} | {', '.join(r['compound_part']) or '-'} |"
            for r in lost], "",
          f"## dev8 topic traps the shipped default opens ({len(traps)})", "",
          "| row | query | unsupported terms | how it passed | `" + name + "` |", "| :--- | :--- | :--- | :--- | :--- |",
          *[f"| {t['id']} | {t['query']} | {', '.join(t['unsupported']) or '-'} | {t['kind']} | {t['arm_decision']} |"
            for t in traps]]
    (ART / "nonkey_posthoc.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    print("\n".join(md))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
