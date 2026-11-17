#!/usr/bin/env python3
"""Citation-aware non-key protocol -> artifacts/nonkey_citation_{calibration,confirm}.{json,md}.

    python scripts/run_nonkey_citation_protocol.py --phase calibrate
    python scripts/run_nonkey_citation_protocol.py --phase confirm     # one shot; refuses to rerun

The confirm spends dev9 and the seed-1110 swaps that the Nov 10 protocol reserved; the
Nov 10 runner refuses its own confirm once this one exists. The Nov 9 ``all`` arm is
scored on the same rows, report-only.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ops_copilot import nonkey_citation_protocol as P  # noqa: E402
from ops_copilot.citation_keep import citation_counts, load_dev9_docs  # noqa: E402
from ops_copilot.config import pre_nonkey_config  # noqa: E402
from ops_copilot.paraphrase_set import load_paraphrase_set  # noqa: E402
from ops_copilot.pipeline import Copilot  # noqa: E402
from ops_copilot.swap_null import MECHANISMS, Row, build_swaps, file_rows, golden_rows, score  # noqa: E402

ART = ROOT / "artifacts"
GOLDEN = [json.loads(x) for x in (ROOT / "data/golden/questions.jsonl").read_text().splitlines() if x.strip()]
SPLIT = json.loads((ROOT / "data/golden/synonym_split.json").read_text())


def bot(name: str) -> Copilot:
    # arms are deltas from the default the protocol was frozen against (non-key rule off),
    # so the records reproduce if the default changes
    return Copilot(config=pre_nonkey_config(**P.ARMS[name]))


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


def _strip(d: dict) -> dict:
    return {k: v for k, v in d.items() if k != "passes"}


def _ids(v) -> str:
    return ", ".join(v) or "none"


def _table(scores: dict[str, dict], cites: dict[str, dict]) -> list[str]:
    ref = scores["shipped"]
    cols = ["swaps", "passed", "pass rate", *MECHANISMS, "ANSWER kept", "decision lost",
            "fixed (wrong evidence)", "budget lost", "new wrong evidence", "must-refuse opened"]
    out = ["| arm | " + " | ".join(cols) + " |", "| :--- |" + " ---: |" * len(cols)]
    for n, d in scores.items():
        c = cites.get(n, {"decision_lost": [], "fixed": [], "budget_lost": 0, "new_wrong": []})
        out.append(
            f"| `{n}` | {d['n_swaps']} | {d['passed']} | {d['rates']['null_pass_rate']:.3f} | "
            + " | ".join(str(d["by_mechanism"][m]) for m in MECHANISMS)
            + f" | {d['answered']}/{d['n_answer_rows']} | {ref['answered'] - d['answered']} | {len(c['fixed'])}"
            f" | {c['budget_lost']} | {len(c['new_wrong'])} | {d['refuse_opened']}/{d['n_refuse_rows']} |"
        )
    return out


def _cite_lines(cites: dict[str, dict]) -> list[str]:
    return [f"- `{n}`: lost {_ids(c['lost'])}; fixed {_ids(c['fixed'])}; unlabelled lost {_ids(c['unknown_lost'])}; "
            f"new wrong evidence {_ids(c['new_wrong'])}" for n, c in cites.items()]


def calibrate() -> int:
    rows = golden_rows() + file_rows(P.CAL_FILES)
    drows = golden_dicts() + dict_rows(P.CAL_FILES)
    ref_swaps = Copilot(config=pre_nonkey_config(passage_support_known_words=True))
    swaps = build_swaps(golden_rows() + file_rows(P.SWAP_BASE_FILES), ref_swaps, draws=P.CAL_DRAWS, seed=P.CAL_SEED)
    bots = {n: bot(n) for n in P.ARMS}
    scores = {n: score(b, rows, swaps).as_dict() for n, b in bots.items()}
    cites = {n: citation_counts(b, bots["shipped"], drows, GOLDEN) for n, b in bots.items() if n != "shipped"}
    picked = P.pick(scores, cites)
    out = {"rows": len(rows), "swaps": len(swaps), "picked": picked, "expected_pick": P.EXPECTED_PICK,
           "arms": {n: _strip(d) for n, d in scores.items()}, "citation": cites,
           "passes": {n: d["passes"] for n, d in scores.items()}}
    (ART / "nonkey_citation_calibration.json").write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8")
    md = ["# Citation-aware non-key protocol, calibration re-score (golden + dev2-dev6 + dev8)", "",
          f"{len(rows)} rows; the Nov 7 {len(swaps)} swaps ({P.CAL_DRAWS} random corpus words per salient term, seed {P.CAL_SEED}). "
          "Budget lost = right-evidence losses + losses on rows without an evidence label; a refused wrong-evidence "
          "answer is fixed, not lost. This re-scores a calibration that was already seen (see the protocol docstring).", "",
          *_table(scores, cites), "", *_cite_lines(cites), "",
          "`all` is the Nov 9 reference and cannot be picked. "
          + (f"Picked: `{picked}` (expected before the re-score: `{P.EXPECTED_PICK}`)." if picked
             else "No arm is eligible; the confirm is not run and dev9 stays unseen.")]
    (ART / "nonkey_citation_calibration.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    print("\n".join(md))
    return 0


def confirm() -> int:
    target = ART / "nonkey_citation_confirm.json"
    if target.exists() or (ART / "nonkey_parts_confirm.json").exists():
        print("confirm already spent")
        return 1
    cal = json.loads((ART / "nonkey_citation_calibration.json").read_text(encoding="utf-8"))
    name = cal["picked"]
    if not name:
        print("no picked arm")
        return 1
    dev9 = dict_rows((P.DEV9_FILE,))
    answer9 = [r for r in dev9 if r["expect_decision"] == "ANSWER"]
    topic9 = [r for r in dev9 if r["expect_decision"] != "ANSWER"]
    drows = answer9 + dict_rows(P.CONFIRM_FILES[1:]) + paraphrase_dicts()
    rows = [Row(str(r["id"]), r["query"], r["expect_decision"]) for r in drows]
    traps = file_rows(P.TRAP_FILES)
    labels = load_dev9_docs()
    bots = {n: bot(n) for n in dict.fromkeys(("shipped", name, *P.REFERENCE_ONLY))}
    swaps = build_swaps(rows, bots["shipped"], draws=P.CONFIRM_DRAWS, seed=P.CONFIRM_SEED)
    scores = {n: score(b, rows, swaps).as_dict() for n, b in bots.items()}
    cites = {n: citation_counts(b, bots["shipped"], drows, GOLDEN, labels) for n, b in bots.items() if n != "shipped"}
    attr = {n: [t.id for t in traps if b.ask(t.query).decision.value == "ANSWER"] for n, b in bots.items()}
    topic = {n: [r["id"] for r in topic9 if b.ask(r["query"]).decision.value == "ANSWER"] for n, b in bots.items()}
    dev9_ok = {n: sum(b.ask(r["query"]).decision.value == "ANSWER" for r in answer9) for n, b in bots.items()}
    held = heldout_answer_ids()
    by_id = {r["id"]: r for r in drows}
    held_ok = {n: sum(b.ask(by_id[i]["query"]).decision.value == "ANSWER" for i in held) for n, b in bots.items()}
    ship = P.ships(scores[name], scores["shipped"], cites[name], len(attr[name]), len(topic[name]), len(topic["shipped"]))
    out = {"arm": name, "rows": len(rows), "swaps": len(swaps), "attribute_trap_opens": attr,
           "topic_trap_opens": topic, "dev9_answered": dev9_ok, "n_dev9_answer": len(answer9),
           "heldout_answer": held_ok, "n_heldout_answer": len(held), "citation": cites, "ships": ship,
           "arms": {n: _strip(d) for n, d in scores.items()}, "passes": {n: d["passes"] for n, d in scores.items()}}
    target.write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8")
    md = [f"# Citation-aware non-key protocol, one-shot confirm (`{name}`)", "",
          f"Rows: dev9 wordy ({len(answer9)}) + dev7 + fresh + the 203-row robustness set ({len(rows)}); "
          f"{len(swaps)} swaps, seed {P.CONFIRM_SEED}.", "", *_table(scores, cites), "", *_cite_lines(cites), "",
          "dev9 wordy rows answered: " + ", ".join(f"`{n}` {v}/{len(answer9)}" for n, v in dev9_ok.items()) + ".",
          f"dev9 topic traps opened ({len(topic9)}): " + ", ".join(f"`{n}` {len(v)} [{_ids(v)}]" for n, v in topic.items()) + ".",
          "Attribute-trap opens (114 rows, v1-v3): " + ", ".join(f"`{n}` {len(v)}" for n, v in attr.items()) + ".",
          f"Held-out ANSWER rows answered ({len(held)}, report-only): " + ", ".join(f"`{n}` {v}" for n, v in held_ok.items()) + ".",
          f"Ships: **{'on' if ship else 'off'}**."]
    (ART / "nonkey_citation_confirm.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    print("\n".join(md))
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--phase", choices=("calibrate", "confirm"), required=True)
    a = ap.parse_args()
    return calibrate() if a.phase == "calibrate" else confirm()


if __name__ == "__main__":
    raise SystemExit(main())
