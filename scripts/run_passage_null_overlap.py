#!/usr/bin/env python3
"""Post-hoc: no percentile cut separates traps from keep rows -> artifacts/passage_null_overlap.{json,md}.

``ops_copilot/passage_null_overlap.py``; selects nothing, changes no config.
Rows: 171 calibration rows and all 76 attribute traps (both sets, all spent).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ops_copilot.attribute_traps import load_traps  # noqa: E402
from ops_copilot.attribute_traps_v2 import load_traps_v2  # noqa: E402
from ops_copilot.datamuse_dev5 import calibration_rows  # noqa: E402
from ops_copilot.passage_null_overlap import run  # noqa: E402


def main() -> int:
    rows = calibration_rows() + load_traps() + load_traps_v2()
    out = run(rows)
    p, calls = out["profile"], out["calls"]
    art = ROOT / "artifacts"
    (art / "passage_null_overlap.json").write_text(json.dumps(out, indent=1, sort_keys=True) + "\n")

    def fmt(rid):
        return "; ".join(f"{w} <- {c} {x:.3f}" for w, c, x in calls[rid])

    lines = [
        "# Can any whole-pool percentile cut separate traps from keep rows? (post-hoc, `passage_null_overlap.py`)", "",
        f"Rows: {out['n_rows']} (171 calibration, 36 + 40 attribute traps; all spent). Pool mode, sticky, cut grid "
        "0.000-1.000 step 0.002.", "",
        f"Worst trap: open up to q = {p['worst_trap_cut']:.3f}. ANSWER rows that pool mode keeps only at or below that "
        f"cut: {len(p['keep_rows_below_worst_trap'])} ({', '.join(p['keep_rows_below_worst_trap'])}). "
        f"Free and safe cuts: {len(p['free_and_safe_cuts'])}.", "",
        "| must-refuse row | opens up to q | calls (query word <- credited passage word, pool percentile) |",
        "| :--- | ---: | :--- |",
    ]
    for rid, q in p["open_up_to"].items():
        lines.append(f"| {rid} | {q:.3f} | {fmt(rid)} |")
    lines += ["", "| ANSWER row | kept up to q | calls |", "| :--- | ---: | :--- |"]
    for rid, q in p["kept_up_to"].items():
        if q <= 0.5:
            lines.append(f"| {rid} | {q:.3f} | {fmt(rid)} |")
    lines += ["", "Every trap that opens is credited by a generic passage word (`one`, `two`, `other`, `only`, "
              "`percent`, `adds`, `region`, `default`, `rolling`, `bot`, `utc`, `rule`). Most keep rows at the same "
              "percentiles are credited by a real substitute (`schedule`, `remaining`, `rotation`), but not all: "
              "d3-02 rides `today <- only / time / bad` and d2-09 `manual <- flag / checkout`. The percentile "
              "measures how much the passage prefers the word, not whether the credited word means the same "
              "thing, so no cut separates them (labels by hand, one person's judgement).", ""]
    (art / "passage_null_overlap.md").write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
