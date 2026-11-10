#!/usr/bin/env python3
"""Post-hoc reading of the compound-parts calibration -> artifacts/nonkey_parts_posthoc.{json,md}.

Selects nothing: the calibration picked no arm and that call stands.
"""

from __future__ import annotations

import dataclasses
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ops_copilot import nonkey_parts_protocol as P  # noqa: E402
from ops_copilot.config import CopilotConfig  # noqa: E402
from ops_copilot.eval import load_golden  # noqa: E402
from ops_copilot.nonkey_parts_posthoc import read_lost  # noqa: E402
from ops_copilot.pipeline import Copilot  # noqa: E402

ART = ROOT / "artifacts"
ARM = "all_hyphen"


def main() -> int:
    cal = json.loads((ART / "nonkey_parts_calibration.json").read_text(encoding="utf-8"))
    ids = [r["id"] for r in cal["lost_rows"][ARM]]
    rows = {}
    for rel in P.CAL_FILES:
        for line in (ROOT / rel).read_text(encoding="utf-8").splitlines():
            if line.strip():
                r = json.loads(line)
                rows[r["id"]] = r
    golden = load_golden()
    shipped = Copilot()
    arm = Copilot(config=dataclasses.replace(CopilotConfig(), **P.ARMS[ARM]))
    out = [read_lost(shipped, arm, rows[i], golden) for i in ids]
    (ART / "nonkey_parts_posthoc.json").write_text(json.dumps({"arm": ARM, "lost": out}, indent=2) + "\n",
                                                    encoding="utf-8")
    md = [f"# Compound parts, post-hoc reading of the 3 rows `{ARM}` still loses (selects nothing)", "",
          "| row | query | word named | shipped cites | clean source cites | reading |",
          "| :--- | :--- | :--- | :--- | :--- | :--- |",
          *[f"| {r['id']} | {r['query']} | {', '.join(r['words'])} | {', '.join(r['shipped_cited'])} | "
            f"{', '.join(r['source_cited']) or 'n/a'} | {r['reading']} |" for r in out]]
    (ART / "nonkey_parts_posthoc.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    print("\n".join(md))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
