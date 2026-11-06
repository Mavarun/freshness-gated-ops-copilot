#!/usr/bin/env python3
"""Verified did-you-mean rewrites protocol -> artifacts/rewrite_suggest_{calibration,confirm}.{json,md}.

    python scripts/run_rewrite_suggest_protocol.py --phase calibrate
    python scripts/run_rewrite_suggest_protocol.py --phase confirm     # one shot; refuses to rerun
    python scripts/run_rewrite_suggest_protocol.py --phase posthoc     # strict anchors, never changes the ship call
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ops_copilot.rewrite_suggest_eval import (  # noqa: E402
    CALIBRATION_FILES,
    CONFIRM_FILES,
    load_heldout_rows,
    load_rows,
    score_arm,
)
from ops_copilot.rewrite_suggest_protocol import ARMS, NULL_DRAWS, SEED, pick, ships  # noqa: E402

ART = ROOT / "artifacts"
COLS = ("coverage", "doc_hit_1", "anchor_hit_1", "anchor_hit_3", "anchor_precision_1", "trap_invitation",
        "null_verify_rate")


def _table(scores: dict[str, dict]) -> list[str]:
    lines = ["| arm | rescuable | traps | " + " | ".join(COLS) + " |", "| :--- |" + " ---: |" * (len(COLS) + 2)]
    for name, d in scores.items():
        r = d["rates"]
        lines.append(f"| `{name}` | {d['n_rescuable']} | {d['n_traps']} | "
                     + " | ".join(f"{r[c]:.3f}" for c in COLS) + " |")
    return lines


def calibrate() -> int:
    rows = load_rows(CALIBRATION_FILES)
    scores = {n: score_arm(rows, c, null_draws=NULL_DRAWS if n == "context" else 0, seed=SEED).as_dict()
              for n, c in ARMS.items()}
    picked = pick({n: d["rates"] for n, d in scores.items()})
    out = {"files": list(CALIBRATION_FILES), "picked": picked,
           "arms": {n: {k: v for k, v in d.items() if k != "rows"} for n, d in scores.items()},
           "rows": {n: d["rows"] for n, d in scores.items()}}
    (ART / "rewrite_suggest_calibration.json").write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8")
    md = ["# Verified rewrites, calibration (dev2-dev6)", "",
          "Null control (`context` row only): random corpus words swapped for the missing term.", "",
          *_table(scores), "", f"Picked: `{picked}`." if picked else "No arm is eligible; confirm is not run."]
    (ART / "rewrite_suggest_calibration.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    print("\n".join(md))
    return 0


def confirm() -> int:
    target = ART / "rewrite_suggest_confirm.json"
    if target.exists():
        print("confirm already spent:", target)
        return 1
    cal = json.loads((ART / "rewrite_suggest_calibration.json").read_text(encoding="utf-8"))
    name = cal["picked"]
    if not name:
        print("no picked arm")
        return 1
    cfg = ARMS[name]
    pooled = score_arm(load_rows(CONFIRM_FILES), cfg, null_draws=NULL_DRAWS, seed=SEED).as_dict()
    held = score_arm(load_heldout_rows(), cfg, null_draws=NULL_DRAWS, seed=SEED).as_dict()
    ship = ships(pooled["rates"], held["anchor_hit_3"])
    out = {"arm": name, "pooled": pooled, "heldout": held, "ships": ship}
    target.write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8")
    md = [f"# Verified rewrites, one-shot confirm (`{name}`)", "", *_table({"dev7+fresh": pooled, "heldout": held}),
          "", f"Held-out anchor hits in top 3: {held['anchor_hit_3']} of {held['n_rescuable']}.",
          f"Ships: **{'on' if ship else 'off'}**.", "", "## Held-out rows", ""]
    for r in held["rows"]:
        md.append(f"- `{r['id']}` ({r['kind']}): " + ("; ".join(f"`{q}`" for q in r["suggestions"]) or "no suggestion"))
    (ART / "rewrite_suggest_confirm.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    print("\n".join(md))
    return 0


def posthoc() -> int:
    """Strict-slot anchors for every arm on calibration and on the spent confirm rows."""
    conf = json.loads((ART / "rewrite_suggest_confirm.json").read_text(encoding="utf-8"))
    sets = {"calibration": load_rows(CALIBRATION_FILES), "dev7+fresh": load_rows(CONFIRM_FILES),
            "heldout": load_heldout_rows()}
    out: dict = {"confirm_arm": conf["arm"], "confirm_ships": conf["ships"], "sets": {}}
    md = ["# Verified rewrites, post-hoc strict anchors (does not change the ship call)", "",
          f"Confirm arm `{conf['arm']}` shipped **{'on' if conf['ships'] else 'off'}**. "
          "Strict = gold word placed in the slot of the word the user typed.", "",
          "| set | arm | rescuable | anchor_hit_3 | strict_anchor_hit_3 | trap_invitation |",
          "| :--- | :--- | ---: | ---: | ---: | ---: |"]
    for set_name, rows in sets.items():
        out["sets"][set_name] = {}
        for name, cfg in ARMS.items():
            d = score_arm(rows, cfg).as_dict()
            out["sets"][set_name][name] = {k: v for k, v in d.items() if k != "rows"}
            r = d["rates"]
            md.append(f"| {set_name} | `{name}` | {d['n_rescuable']} | {d['anchor_hit_3']} | "
                      f"{d['strict_anchor_hit_3']} | {r['trap_invitation']:.3f} |")
    (ART / "rewrite_suggest_posthoc.json").write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8")
    (ART / "rewrite_suggest_posthoc.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    print("\n".join(md))
    return 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--phase", choices=("calibrate", "confirm", "posthoc"), required=True)
    sys.exit({"calibrate": calibrate, "confirm": confirm, "posthoc": posthoc}[ap.parse_args().phase]())
