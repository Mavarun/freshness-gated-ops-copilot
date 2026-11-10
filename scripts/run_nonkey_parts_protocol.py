#!/usr/bin/env python3
"""Compound-parts protocol -> artifacts/nonkey_parts_{calibration,confirm}.{json,md}.

    python scripts/run_nonkey_parts_protocol.py --phase calibrate
    python scripts/run_nonkey_parts_protocol.py --phase confirm     # one shot; refuses to rerun

The confirm also scores the Nov 9 ``all`` arm on the same rows, report-only.
"""

from __future__ import annotations

import argparse
import dataclasses
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ops_copilot import nonkey_parts_protocol as P  # noqa: E402
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
    swaps = build_swaps(golden_rows() + file_rows(P.SWAP_BASE_FILES), ref_swaps, draws=P.CAL_DRAWS, seed=P.CAL_SEED)
    bots = {n: bot(n) for n in P.ARMS}
    scores = {n: score(b, rows, swaps).as_dict() for n, b in bots.items()}
    picked = P.pick(scores)
    lost = {n: _lost_rows(b, bots["shipped"], rows) for n, b in bots.items() if n != "shipped"}
    out = {"rows": len(rows), "swaps": len(swaps), "picked": picked,
           "arms": {n: _strip(d) for n, d in scores.items()},
           "lost_rows": lost, "passes": {n: d["passes"] for n, d in scores.items()}}
    (ART / "nonkey_parts_calibration.json").write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8")
    md = ["# Compound parts for the non-key rule, calibration (golden + dev2-dev6 + dev8)", "",
          f"{len(rows)} rows (dev8's 16 topic traps count as must-refuse rows); the Nov 7 {len(swaps)} swaps ({P.CAL_DRAWS} random corpus words per salient term, "
          f"seed {P.CAL_SEED}). Mechanism columns count passed swaps by what supported the swapped-in word.", "",
          *_table(scores, scores["shipped"]), "",
          "Calibration ANSWER rows lost per arm: "
          + "; ".join(f"`{n}` {', '.join(r['id'] for r in v) or 'none'}" for n, v in lost.items()), "",
          f"`all` is the Nov 9 reference and cannot be picked. "
          + (f"Picked: `{picked}`." if picked else "No arm is eligible; confirm is not run.")]
    (ART / "nonkey_parts_calibration.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    print("\n".join(md))
    return 0


def confirm() -> int:
    target = ART / "nonkey_parts_confirm.json"
    if target.exists():
        print("confirm already spent:", target)
        return 1
    cal = json.loads((ART / "nonkey_parts_calibration.json").read_text(encoding="utf-8"))
    name = cal["picked"]
    if not name:
        print("no picked arm")
        return 1
    dev9 = file_rows((P.DEV9_FILE,))
    answer_rows = [r for r in dev9 if r.expect == "ANSWER"]
    topic_traps = [r for r in dev9 if r.expect != "ANSWER"]
    rows = answer_rows + file_rows(P.CONFIRM_FILES[1:]) + [
        Row(str(r["id"]), r["query"], r["expect_decision"]) for r in load_paraphrase_set()]
    traps = file_rows(P.TRAP_FILES)
    bots = {n: bot(n) for n in dict.fromkeys(("shipped", name, *P.REFERENCE_ONLY))}
    swaps = build_swaps(rows, bots["shipped"], draws=P.CONFIRM_DRAWS, seed=P.CONFIRM_SEED)
    scores = {n: score(b, rows, swaps).as_dict() for n, b in bots.items()}
    attr = {n: [t.id for t in traps if b.ask(t.query).decision.value == "ANSWER"] for n, b in bots.items()}
    topic = {n: [t.id for t in topic_traps if b.ask(t.query).decision.value == "ANSWER"] for n, b in bots.items()}
    dev9_kept = {n: sum(b.ask(r.query).decision.value == "ANSWER" for r in answer_rows) for n, b in bots.items()}
    ship = P.ships(scores[name], scores["shipped"], len(attr[name]), len(topic[name]), len(topic["shipped"]))
    lost = _lost_rows(bots[name], bots["shipped"], rows)
    lost_ref = {n: _lost_rows(bots[n], bots["shipped"], rows) for n in P.REFERENCE_ONLY if n != name}
    out = {"arm": name, "rows": len(rows), "swaps": len(swaps), "attribute_trap_opens": attr,
           "topic_trap_opens": topic, "dev9_answered": dev9_kept, "lost_rows": lost,
           "reference_lost_rows": lost_ref, "ships": ship,
           "arms": {n: _strip(d) for n, d in scores.items()}, "passes": {n: d["passes"] for n, d in scores.items()}}
    target.write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8")
    md = [f"# Compound parts for the non-key rule, one-shot confirm (`{name}`)", "",
          f"Rows: dev9 wordy ({len(answer_rows)}) + dev7 + fresh + the 203-row robustness set ({len(rows)}); "
          f"{len(swaps)} swaps, seed {P.CONFIRM_SEED}.", "", *_table(scores, scores["shipped"]), "",
          "dev9 wordy rows answered: " + ", ".join(f"`{n}` {v}/{len(answer_rows)}" for n, v in dev9_kept.items()) + ".",
          "dev9 topic traps opened (16): " + ", ".join(f"`{n}` {len(v)} {v}" for n, v in topic.items()) + ".",
          "Attribute-trap opens (114 rows, v1-v3): " + ", ".join(f"`{n}` {len(v)}" for n, v in attr.items()) + ".",
          f"Answered rows lost by `{name}`: " + (", ".join(f"{r['id']} ({'/'.join(r['nonkey_unsupported']) or r['decision']})" for r in lost) or "none"),
          *[f"Answered rows lost by `{n}` (reference, report-only): " + (", ".join(f"{r['id']} ({'/'.join(r['nonkey_unsupported']) or r['decision']})" for r in v) or "none") for n, v in lost_ref.items()],
          f"Ships: **{'on' if ship else 'off'}**."]
    (ART / "nonkey_parts_confirm.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    print("\n".join(md))
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--phase", choices=("calibrate", "confirm"), required=True)
    a = ap.parse_args()
    return calibrate() if a.phase == "calibrate" else confirm()


if __name__ == "__main__":
    raise SystemExit(main())
