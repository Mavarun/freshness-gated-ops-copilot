#!/usr/bin/env python3
"""Answer-side swap null control -> artifacts/swap_null_{calibration,confirm}.{json,md}.

    python scripts/run_swap_null_protocol.py --phase calibrate
    python scripts/run_swap_null_protocol.py --phase confirm     # one shot; refuses to rerun
"""

from __future__ import annotations

import argparse
import dataclasses
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ops_copilot.config import CopilotConfig  # noqa: E402
from ops_copilot.paraphrase_set import load_paraphrase_set  # noqa: E402
from ops_copilot.pipeline import Copilot  # noqa: E402
from ops_copilot import swap_null_protocol as P  # noqa: E402
from ops_copilot.swap_null import MECHANISMS, Row, build_swaps, file_rows, golden_rows, score  # noqa: E402

ART = ROOT / "artifacts"


def bot(name: str) -> Copilot:
    return Copilot(config=dataclasses.replace(CopilotConfig(), **P.ARMS[name]))


def _table(scores: dict[str, dict], ref: dict) -> list[str]:
    cols = ["swaps", "passed", "pass rate", *MECHANISMS, "ANSWER kept", "lost", "must-refuse opened"]
    out = ["| arm | " + " | ".join(cols) + " |", "| :--- |" + " ---: |" * len(cols)]
    for n, d in scores.items():
        out.append(
            f"| `{n}` | {d['n_swaps']} | {d['passed']} | {d['rates']['null_pass_rate']:.3f} | "
            + " | ".join(str(d["by_mechanism"][m]) for m in MECHANISMS)
            + f" | {d['answered']}/{d['n_answer_rows']} | {P.lost(d, ref)} | {d['refuse_opened']}/{d['n_refuse_rows']} |"
        )
    return out


def _strip(d: dict) -> dict:
    return {k: v for k, v in d.items() if k != "passes"}


def calibrate() -> int:
    rows = golden_rows() + file_rows(P.CAL_FILES)
    swaps = build_swaps(rows, bot("shipped"), draws=P.CAL_DRAWS, seed=P.CAL_SEED)
    scores = {n: score(bot(n), rows, swaps).as_dict() for n in P.ARMS}
    picked = P.pick(scores)
    out = {"rows": len(rows), "swaps": len(swaps), "picked": picked,
           "arms": {n: _strip(d) for n, d in scores.items()},
           "passes": {n: d["passes"] for n, d in scores.items()}}
    (ART / "swap_null_calibration.json").write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8")
    md = ["# Swap null control, calibration (golden + dev2-dev6)", "",
          f"{len(rows)} rows; {len(swaps)} swaps ({P.CAL_DRAWS} random corpus words per salient term of every row "
          f"the shipped default answers, seed {P.CAL_SEED}). Mechanism columns count passed swaps by what "
          "supported the swapped-in word.", "", *_table(scores, scores["shipped"]), "",
          f"Picked: `{picked}`." if picked else "No arm is eligible; confirm is not run."]
    (ART / "swap_null_calibration.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    print("\n".join(md))
    return 0


def confirm() -> int:
    target = ART / "swap_null_confirm.json"
    if target.exists():
        print("confirm already spent:", target)
        return 1
    cal = json.loads((ART / "swap_null_calibration.json").read_text(encoding="utf-8"))
    name = cal["picked"]
    if not name:
        print("no picked arm")
        return 1
    rows = file_rows(P.CONFIRM_FILES) + [Row(str(r["id"]), r["query"], r["expect_decision"])
                                         for r in load_paraphrase_set()]
    traps = file_rows(P.TRAP_FILES)
    swaps = build_swaps(rows, bot("shipped"), draws=P.CONFIRM_DRAWS, seed=P.CONFIRM_SEED)
    scores = {n: score(bot(n), rows, swaps).as_dict() for n in ("shipped", name)}
    opens = {n: sum(bot(n).ask(t.query).decision.value == "ANSWER" for t in traps) for n in scores}
    ship = P.ships(scores[name], scores["shipped"], opens[name])
    out = {"arm": name, "rows": len(rows), "swaps": len(swaps), "trap_opens": opens, "ships": ship,
           "arms": {n: _strip(d) for n, d in scores.items()}, "passes": {n: d["passes"] for n, d in scores.items()}}
    target.write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8")
    md = [f"# Swap null control, one-shot confirm (`{name}`)", "",
          f"Rows: dev7 + fresh + the 203-row robustness set ({len(rows)}); {len(swaps)} swaps, seed {P.CONFIRM_SEED}.",
          "", *_table(scores, scores["shipped"]), "",
          f"Attribute-trap opens (114 rows, v1-v3): shipped {opens['shipped']}, `{name}` {opens[name]}.",
          f"Ships: **{'on' if ship else 'off'}**."]
    (ART / "swap_null_confirm.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    print("\n".join(md))
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--phase", choices=("calibrate", "confirm"), required=True)
    a = ap.parse_args()
    return calibrate() if a.phase == "calibrate" else confirm()


if __name__ == "__main__":
    raise SystemExit(main())
