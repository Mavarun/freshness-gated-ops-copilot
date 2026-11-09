#!/usr/bin/env python3
"""Non-key coverage rule protocol -> artifacts/nonkey_{calibration,confirm}.{json,md}.

    python scripts/run_nonkey_protocol.py --phase calibrate
    python scripts/run_nonkey_protocol.py --phase confirm     # one shot; refuses to rerun
"""

from __future__ import annotations

import argparse
import dataclasses
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ops_copilot import nonkey_coverage_protocol as P  # noqa: E402
from ops_copilot.config import CopilotConfig  # noqa: E402
from ops_copilot.paraphrase_set import load_paraphrase_set  # noqa: E402
from ops_copilot.pipeline import Copilot  # noqa: E402
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


def _lost_rows(arm: Copilot, ref: Copilot, rows: list[Row]) -> list[dict]:
    """ANSWER rows the shipped default answers and the arm does not (with the named words)."""
    out = []
    for r in rows:
        if r.expect != "ANSWER" or ref.ask(r.query).decision.value != "ANSWER":
            continue
        res = arm.ask(r.query)
        if res.decision.value != "ANSWER":
            out.append({"id": r.id, "query": r.query, "decision": res.decision.value,
                        "nonkey_unsupported": list(res.grounding.nonkey_unsupported) if res.grounding else []})
    return out


def calibrate() -> int:
    rows = golden_rows() + file_rows(P.CAL_FILES)
    ref_swaps = Copilot(config=dataclasses.replace(CopilotConfig(), passage_support_known_words=True))
    swaps = build_swaps(rows, ref_swaps, draws=P.CAL_DRAWS, seed=P.CAL_SEED)
    bots = {n: bot(n) for n in P.ARMS}
    scores = {n: score(b, rows, swaps).as_dict() for n, b in bots.items()}
    picked = P.pick(scores)
    lost = {n: _lost_rows(b, bots["shipped"], rows) for n, b in bots.items() if n != "shipped"}
    out = {"rows": len(rows), "swaps": len(swaps), "picked": picked,
           "arms": {n: _strip(d) for n, d in scores.items()},
           "lost_rows": lost, "passes": {n: d["passes"] for n, d in scores.items()}}
    (ART / "nonkey_calibration.json").write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8")
    md = ["# Non-key coverage rule, calibration (golden + dev2-dev6)", "",
          f"{len(rows)} rows; the Nov 7 {len(swaps)} swaps ({P.CAL_DRAWS} random corpus words per salient term, "
          f"seed {P.CAL_SEED}). Mechanism columns count passed swaps by what supported the swapped-in word.", "",
          *_table(scores, scores["shipped"]), "",
          "Calibration ANSWER rows lost per arm: "
          + "; ".join(f"`{n}` {', '.join(r['id'] for r in v) or 'none'}" for n, v in lost.items()), "",
          f"Picked: `{picked}`." if picked else "No arm is eligible; confirm is not run."]
    (ART / "nonkey_calibration.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    print("\n".join(md))
    return 0


def confirm() -> int:
    target = ART / "nonkey_confirm.json"
    if target.exists():
        print("confirm already spent:", target)
        return 1
    cal = json.loads((ART / "nonkey_calibration.json").read_text(encoding="utf-8"))
    name = cal["picked"]
    if not name:
        print("no picked arm")
        return 1
    dev8 = file_rows((P.DEV8_FILE,))
    answer_rows = [r for r in dev8 if r.expect == "ANSWER"]
    topic_traps = [r for r in dev8 if r.expect != "ANSWER"]
    rows = answer_rows + file_rows(P.CONFIRM_FILES[1:]) + [
        Row(str(r["id"]), r["query"], r["expect_decision"]) for r in load_paraphrase_set()]
    traps = file_rows(P.TRAP_FILES)
    bots = {n: bot(n) for n in ("shipped", name)}
    swaps = build_swaps(rows, bots["shipped"], draws=P.CONFIRM_DRAWS, seed=P.CONFIRM_SEED)
    scores = {n: score(b, rows, swaps).as_dict() for n, b in bots.items()}
    attr = {n: [t.id for t in traps if b.ask(t.query).decision.value == "ANSWER"] for n, b in bots.items()}
    topic = {n: [t.id for t in topic_traps if b.ask(t.query).decision.value == "ANSWER"] for n, b in bots.items()}
    dev8_kept = {n: sum(b.ask(r.query).decision.value == "ANSWER" for r in answer_rows) for n, b in bots.items()}
    ship = P.ships(scores[name], scores["shipped"], len(attr[name]), len(topic[name]), len(topic["shipped"]))
    lost = _lost_rows(bots[name], bots["shipped"], rows)
    out = {"arm": name, "rows": len(rows), "swaps": len(swaps), "attribute_trap_opens": attr,
           "topic_trap_opens": topic, "dev8_answered": dev8_kept, "lost_rows": lost, "ships": ship,
           "arms": {n: _strip(d) for n, d in scores.items()}, "passes": {n: d["passes"] for n, d in scores.items()}}
    target.write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8")
    md = [f"# Non-key coverage rule, one-shot confirm (`{name}`)", "",
          f"Rows: dev8 wordy ({len(answer_rows)}) + dev7 + fresh + the 203-row robustness set ({len(rows)}); "
          f"{len(swaps)} swaps, seed {P.CONFIRM_SEED}.", "", *_table(scores, scores["shipped"]), "",
          f"dev8 wordy rows answered: shipped {dev8_kept['shipped']}/{len(answer_rows)}, `{name}` {dev8_kept[name]}/{len(answer_rows)}.",
          f"dev8 topic traps opened (16): shipped {len(topic['shipped'])} {topic['shipped']}, `{name}` {len(topic[name])} {topic[name]}.",
          f"Attribute-trap opens (114 rows, v1-v3): shipped {len(attr['shipped'])}, `{name}` {len(attr[name])}.",
          "Answered rows lost: " + (", ".join(f"{r['id']} ({'/'.join(r['nonkey_unsupported']) or r['decision']})" for r in lost) or "none"),
          f"Ships: **{'on' if ship else 'off'}**."]
    (ART / "nonkey_confirm.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    print("\n".join(md))
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--phase", choices=("calibrate", "confirm"), required=True)
    a = ap.parse_args()
    return calibrate() if a.phase == "calibrate" else confirm()


if __name__ == "__main__":
    raise SystemExit(main())
