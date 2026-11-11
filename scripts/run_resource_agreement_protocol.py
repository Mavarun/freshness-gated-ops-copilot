#!/usr/bin/env python3
"""Resource-agreement protocol -> artifacts/resource_agreement_{calibration,confirm}.{json,md}.

    python scripts/run_resource_agreement_protocol.py --phase calibrate
    python scripts/run_resource_agreement_protocol.py --phase confirm     # one shot; refuses to rerun
"""

from __future__ import annotations

import argparse
import dataclasses
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ops_copilot import resource_agreement_protocol as P  # noqa: E402
from ops_copilot.citation_keep import citation_counts  # noqa: E402
from ops_copilot.config import CopilotConfig  # noqa: E402
from ops_copilot.paraphrase_set import load_paraphrase_set  # noqa: E402
from ops_copilot.pipeline import Copilot  # noqa: E402
from ops_copilot.swap_null import MECHANISMS, Row, build_swaps, file_rows, golden_rows, score  # noqa: E402

ART = ROOT / "artifacts"
GOLDEN = [json.loads(x) for x in (ROOT / "data/golden/questions.jsonl").read_text().splitlines() if x.strip()]
SPLIT = json.loads((ROOT / "data/golden/synonym_split.json").read_text())


def bot(name: str) -> Copilot:
    return Copilot(config=dataclasses.replace(CopilotConfig(), **P.ARMS[name]))


def dict_rows(files) -> list[dict]:
    out = []
    for rel in files:
        out += [json.loads(x) for x in (ROOT / rel).read_text().splitlines() if x.strip()]
    return out


def golden_dicts() -> list[dict]:
    return [dict(r, id=f"golden-{i:02d}", source_index=i) for i, r in enumerate(GOLDEN)]


def paraphrase_dicts() -> list[dict]:
    return [dict(r, id=str(r["id"])) for r in load_paraphrase_set()]


def heldout_answer_ids() -> list[str]:
    held = {k for k, v in SPLIT["rows"].items() if v["split"] == "heldout"}
    return [r["id"] for r in paraphrase_dicts() if r["id"] in held and r["expect_decision"] == "ANSWER"]


def _table(scores: dict[str, dict], ref: dict, wrong: dict[str, int]) -> list[str]:
    cols = ["swaps", "passed", "pass rate", *MECHANISMS, "ANSWER kept", "gain", "must-refuse opened", "new wrong evidence"]
    out = ["| arm | " + " | ".join(cols) + " |", "| :--- |" + " ---: |" * len(cols)]
    for n, d in scores.items():
        out.append(
            f"| `{n}` | {d['n_swaps']} | {d['passed']} | {d['rates']['null_pass_rate']:.3f} | "
            + " | ".join(str(d["by_mechanism"][m]) for m in MECHANISMS)
            + f" | {d['answered']}/{d['n_answer_rows']} | {P.gain(d, ref):+d} | {d['refuse_opened']}/{d['n_refuse_rows']} | {wrong.get(n, 0)} |"
        )
    return out


def _strip(d: dict) -> dict:
    return {k: v for k, v in d.items() if k != "passes"}


def _changed(arm: Copilot, ref: Copilot, rows: list[dict]) -> list[dict]:
    """Rows whose decision differs between the arm and the shipped default."""
    out = []
    for r in rows:
        a, b = arm.ask(r["query"]), ref.ask(r["query"])
        if a.decision != b.decision:
            out.append({"id": r["id"], "query": r["query"], "expect": r["expect_decision"],
                        "shipped": b.decision.value, "arm": a.decision.value, "arm_cited": list(a.cited_ids)})
    return out


def calibrate() -> int:
    rows = golden_rows() + file_rows(P.CAL_FILES)
    drows = golden_dicts() + dict_rows(P.CAL_FILES)
    ref_swaps = Copilot(config=dataclasses.replace(CopilotConfig(), passage_support_known_words=True))
    swaps = build_swaps(golden_rows() + file_rows(P.SWAP_BASE_FILES), ref_swaps, draws=P.CAL_DRAWS, seed=P.CAL_SEED)
    bots = {n: bot(n) for n in P.ARMS}
    scores = {n: score(b, rows, swaps).as_dict() for n, b in bots.items()}
    cites = {n: citation_counts(b, bots["shipped"], drows, GOLDEN) for n, b in bots.items() if n != "shipped"}
    wrong = {n: len(c["new_wrong"]) for n, c in cites.items()}
    picked = P.pick(scores, wrong)
    changed = {n: _changed(b, bots["shipped"], drows) for n, b in bots.items() if n != "shipped"}
    out = {"rows": len(rows), "swaps": len(swaps), "picked": picked,
           "arms": {n: _strip(d) for n, d in scores.items()}, "citation": cites,
           "changed_rows": changed, "passes": {n: d["passes"] for n, d in scores.items()}}
    (ART / "resource_agreement_calibration.json").write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8")
    md = ["# Resource-agreement backoff, calibration (golden + dev2-dev6 + dev8)", "",
          f"{len(rows)} rows; the Nov 7 {len(swaps)} swaps ({P.CAL_DRAWS} random corpus words per salient term, seed {P.CAL_SEED}). "
          "Mechanism columns count passed swaps by what supported the swapped-in word. "
          "New wrong evidence = arm answers citing other documents than the clean source question.", "",
          *_table(scores, scores["shipped"], wrong), "",
          "Rows whose decision changes per arm: "
          + "; ".join(f"`{n}` " + (", ".join(f"{r['id']} {r['shipped']}->{r['arm']}" for r in v) or "none") for n, v in changed.items()), "",
          (f"Picked: `{picked}`." if picked else "No arm is eligible; the confirm is not run and dev10 stays unseen.")]
    (ART / "resource_agreement_calibration.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    print("\n".join(md))
    return 0


def confirm() -> int:
    target = ART / "resource_agreement_confirm.json"
    if target.exists():
        print("confirm already spent:", target)
        return 1
    cal = json.loads((ART / "resource_agreement_calibration.json").read_text(encoding="utf-8"))
    name = cal["picked"]
    if not name:
        print("no picked arm")
        return 1
    drows = dict_rows(P.CONFIRM_FILES) + paraphrase_dicts()
    rows = [Row(r["id"], r["query"], r["expect_decision"]) for r in drows]
    traps = file_rows(P.TRAP_FILES)
    bots = {n: bot(n) for n in ("shipped", name)}
    swaps = build_swaps(rows, bots["shipped"], draws=P.CONFIRM_DRAWS, seed=P.CONFIRM_SEED)
    scores = {n: score(b, rows, swaps).as_dict() for n, b in bots.items()}
    attr = {n: [t.id for t in traps if b.ask(t.query).decision.value == "ANSWER"] for n, b in bots.items()}
    cites = citation_counts(bots[name], bots["shipped"], drows, GOLDEN)
    held = heldout_answer_ids()
    by_id = {r["id"]: r for r in drows}
    held_ok = {n: sum(b.ask(by_id[i]["query"]).decision.value == "ANSWER" for i in held) for n, b in bots.items()}
    dev10 = [r for r in drows if r["id"].startswith("d10-")]
    dev10_ok = {n: sum(b.ask(r["query"]).decision.value == r["expect_decision"] for r in dev10) for n, b in bots.items()}
    ship = P.ships(scores[name], scores["shipped"], len(attr[name]), len(cites["new_wrong"]))
    changed = _changed(bots[name], bots["shipped"], drows)
    out = {"arm": name, "rows": len(rows), "swaps": len(swaps), "attribute_trap_opens": attr,
           "citation": cites, "heldout_answer": held_ok, "n_heldout_answer": len(held),
           "dev10_correct": dev10_ok, "changed_rows": changed, "ships": ship,
           "arms": {n: _strip(d) for n, d in scores.items()}, "passes": {n: d["passes"] for n, d in scores.items()}}
    target.write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8")
    wrong = {name: len(cites["new_wrong"])}
    md = [f"# Resource-agreement backoff, one-shot confirm (`{name}`)", "",
          f"Rows: dev10 ({len(dev10)}) + dev7 + fresh + the 203-row robustness set ({len(rows)}); "
          f"{len(swaps)} swaps, seed {P.CONFIRM_SEED}.", "", *_table(scores, scores["shipped"], wrong), "",
          "dev10 rows correct: " + ", ".join(f"`{n}` {v}/{len(dev10)}" for n, v in dev10_ok.items()) + ".",
          f"Held-out ANSWER rows answered ({len(held)}): " + ", ".join(f"`{n}` {v}" for n, v in held_ok.items()) + ".",
          "Attribute-trap opens (114 rows, v1-v3): " + ", ".join(f"`{n}` {len(v)}" for n, v in attr.items()) + ".",
          "Changed rows: " + (", ".join(f"{r['id']} {r['shipped']}->{r['arm']} (expect {r['expect']})" for r in changed) or "none") + ".",
          f"Ships: **{'on' if ship else 'off'}**."]
    (ART / "resource_agreement_confirm.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    print("\n".join(md))
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--phase", choices=("calibrate", "confirm"), required=True)
    a = ap.parse_args()
    return calibrate() if a.phase == "calibrate" else confirm()


if __name__ == "__main__":
    raise SystemExit(main())
