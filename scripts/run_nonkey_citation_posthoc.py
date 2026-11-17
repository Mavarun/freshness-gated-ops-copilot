#!/usr/bin/env python3
"""Post-hoc reading of the Nov 17 non-key ship -> artifacts/nonkey_citation_posthoc.{json,md}.

Selects nothing; the ship call stands. Run after the one-shot confirm (dev9 is spent):

1. why the shipped default answers only 12-13 of the 32 dev9 wordy rows, by refusal gate;
2. every row of every committed eval file whose decision differs between the rule-off
   default (up to 2026-11-16) and the shipped default, with the word the rule names and
   whether the change is a fix, a lost answer or a refusal under a different gate.
   dev10 is not read: it stays unseen for its own pre-registered confirm.
"""

from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ops_copilot import nonkey_citation_protocol as P  # noqa: E402
from ops_copilot.citation_keep import evidence_ok, load_dev9_docs  # noqa: E402
from ops_copilot.config import pre_nonkey_config  # noqa: E402
from ops_copilot.paraphrase_set import load_paraphrase_set  # noqa: E402
from ops_copilot.pipeline import Copilot  # noqa: E402

ART = ROOT / "artifacts"
EVAL_FILES = (
    "data/eval/synonym_dev2.jsonl", "data/eval/synonym_dev3.jsonl", "data/eval/synonym_dev4.jsonl",
    "data/eval/synonym_dev5.jsonl", "data/eval/synonym_dev6.jsonl", "data/eval/synonym_dev7.jsonl",
    "data/eval/nonkey_dev8.jsonl", "data/eval/nonkey_dev9.jsonl",
    "data/eval/synonym_fresh.jsonl", "data/eval/attribute_traps.jsonl", "data/eval/attribute_traps_v2.jsonl",
    "data/eval/attribute_traps_v3.jsonl",
)


GOLDEN = [json.loads(x) for x in (ROOT / "data/golden/questions.jsonl").read_text().splitlines() if x.strip()]


def _rows() -> list[dict]:
    out = [dict(r, id=f"golden-{i:02d}") for i, r in enumerate(GOLDEN)]
    for rel in EVAL_FILES:
        out += [json.loads(x) for x in (ROOT / rel).read_text().splitlines() if x.strip()]
    return out + [dict(r, id=str(r["id"])) for r in load_paraphrase_set()]


def effect(expect: str, old: str, new: str, old_evidence: bool | None = None) -> str:
    if new == expect:
        return "fixed"
    if old == expect and expect == "ANSWER":
        if old_evidence is False:
            return "wrong-evidence answer refused"
        return "lost answer" if old_evidence else "lost answer (no evidence label)"
    if old == expect:
        return "refused under another gate" if new.startswith("REFUSE") else "broke"
    return "still wrong"


def main() -> int:
    new, old = Copilot(), Copilot(config=pre_nonkey_config())
    dev9 = [json.loads(x) for x in (ROOT / P.DEV9_FILE).read_text().splitlines() if x.strip()]
    wordy = [r for r in dev9 if r["expect_decision"] == "ANSWER"]
    gates = {n: Counter(b.ask(r["query"]).decision.value for r in wordy) for n, b in (("shipped", new), ("rule off", old))}
    rows = _rows()
    assert len({r["id"] for r in rows}) == len(rows), "duplicate row ids"
    labels = load_dev9_docs()
    changed = []
    for r in rows:
        a, b = new.ask(r["query"]), old.ask(r["query"])
        if a.decision != b.decision:
            ev = evidence_ok(old, r, GOLDEN, labels, result=b)
            changed.append({"id": r["id"], "query": r["query"], "expect": r["expect_decision"],
                            "rule_off": b.decision.value, "shipped": a.decision.value,
                            "rule_off_cited": list(b.cited_ids), "rule_off_evidence_ok": ev,
                            "words": list(a.grounding.nonkey_unsupported) if a.grounding else [],
                            "effect": effect(r["expect_decision"], b.decision.value, a.decision.value, ev)})
    effects = Counter(c["effect"] for c in changed)
    out = {"n_rows": len(rows), "dev9_wordy_gates": {k: dict(v) for k, v in gates.items()},
           "changed": changed, "effects": dict(effects)}
    (ART / "nonkey_citation_posthoc.json").write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8")
    md = ["# Non-key rule shipped (2026-11-17): post-hoc reading (selects nothing)", "",
          "## dev9 wordy rows (32) by decision", "",
          "| decision | shipped | rule off |", "| :--- | ---: | ---: |",
          *[f"| {d} | {gates['shipped'].get(d, 0)} | {gates['rule off'].get(d, 0)} |"
            for d in sorted(set(gates["shipped"]) | set(gates["rule off"]))], "",
          f"## Rows whose decision changes ({len(changed)} of {len(rows)} rows in every committed eval file)", "",
          "| row | query | expected | rule off | shipped | word named | effect |",
          "| :--- | :--- | :--- | :--- | :--- | :--- | :--- |",
          *[f"| `{c['id']}` | {c['query']} | {c['expect']} | {c['rule_off']} | {c['shipped']} | "
            f"{', '.join(c['words']) or '-'} | {c['effect']} |" for c in changed], "",
          "Effects: " + ", ".join(f"{k} {v}" for k, v in sorted(effects.items())) + "."]
    (ART / "nonkey_citation_posthoc.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    print("\n".join(md))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
