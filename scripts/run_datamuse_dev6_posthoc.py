#!/usr/bin/env python3
"""Post-hoc (dev6 is spent): which Datamuse mapping each dev6 row got -> artifacts/datamuse_dev6_posthoc.{json,md}.

Selects nothing and changes no config. For every dev6 row it lists the query's
words the corpus does not know and, under the frozen arm, the corpus word each
one maps to with its Datamuse rank, counter-fitted cosine and corpus-context
support. The sense label (right / wrong sense for this question) is written by
hand in ``SENSE`` after reading the mappings, so it is a judgement, not a
measurement.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ops_copilot.datamuse_dev6 import arm_config  # noqa: E402
from ops_copilot.pipeline import Copilot  # noqa: E402
from ops_copilot.synonym_dev6 import load_dev6  # noqa: E402
from ops_copilot.text import content_tokens  # noqa: E402

# Hand judgement after reading the mappings (post-hoc): does the corpus word
# mean what the query word means *in this question*?
SENSE = {
    ("available", "availability"): "right",
    ("relief", "mitigation"): "right",
    ("custodian", "owner"): "right",
    ("urge", "request"): "wrong",
    ("occupation", "working"): "wrong",
    ("hold", "maintenance"): "wrong",
    ("protocol", "minutes"): "wrong",
    ("country", "region"): "wrong",
}


def diagnose() -> dict:
    bot = Copilot(config=arm_config())
    dm, idf = bot.datamuse, bot.grounder.idf
    conf = json.loads((ROOT / "artifacts" / "datamuse_dev6_confirm.json").read_text())["confirm"]
    rows_out = []
    for r in load_dev6():
        toks = content_tokens(r["query"])
        unknown = [t for t in toks if t not in idf]
        dm.set_context(frozenset(t for t in toks if t in idf))
        maps = []
        for u in unknown:
            ranks = {w: rk for w, rk, _n, _d in dm._rows(u)}
            for n in dm.neighbours(u):
                cos = dm.sense_similarity(u, n.word)
                maps.append({"query_word": u, "corpus_word": n.word, "rank": ranks.get(n.word),
                             "cosine": round(cos, 3) if cos is not None else None,
                             "context": dm.context_support(n.word, u),
                             "sense": SENSE.get((u, n.word), "unlabelled")})
        rows_out.append({"id": r["id"], "query": r["query"], "expect": r["expect_decision"],
                         "off": conf["off"]["decisions"][r["id"]], "on": conf["on"]["decisions"][r["id"]],
                         "unknown": unknown, "mappings": maps})
    dm.set_context(None)
    mapped = [x for x in rows_out if x["mappings"]]
    swaps = [x for x in rows_out if x["id"] in {r["id"] for r in load_dev6() if "swap" in r}]
    return {
        "n_rows": len(rows_out),
        "n_swap_rows": len(swaps),
        "n_swap_rows_with_unknown_word": sum(bool(x["unknown"]) for x in swaps),
        "n_rows_mapped": len(mapped),
        "n_mappings_right_sense": sum(m["sense"] == "right" for x in mapped for m in x["mappings"]),
        "n_mappings_wrong_sense": sum(m["sense"] == "wrong" for x in mapped for m in x["mappings"]),
        "n_mapped_and_decision_changed": sum(x["off"] != x["on"] for x in mapped),
        "rows": rows_out,
    }


def main() -> int:
    out = diagnose()
    lines = [
        "# dev6 post-hoc: what the Datamuse arm mapped (dev6 spent; selects nothing)", "",
        f"{out['n_swap_rows_with_unknown_word']} of {out['n_swap_rows']} swap rows put a word the corpus does not "
        f"know into the query; the arm maps a word in {out['n_rows_mapped']} of {out['n_rows']} rows. "
        f"By hand: {out['n_mappings_right_sense']} right-sense, {out['n_mappings_wrong_sense']} wrong-sense "
        f"mappings; {out['n_mapped_and_decision_changed']} mapped rows change decision.", "",
        "| row | query | expect | off -> on | query word -> corpus word | rank | cosine | context | sense |",
        "| :--- | :--- | :--- | :--- | :--- | ---: | ---: | ---: | :--- |",
    ]
    for x in out["rows"]:
        for m in x["mappings"]:
            lines.append(f"| {x['id']} | {x['query']} | {x['expect']} | {x['off']} -> {x['on']} | "
                         f"{m['query_word']} -> {m['corpus_word']} | {m['rank']} | {m['cosine']} | "
                         f"{m['context']} | {m['sense']} |")
    art = ROOT / "artifacts"
    (art / "datamuse_dev6_posthoc.json").write_text(json.dumps(out, indent=1, sort_keys=True) + "\n")
    (art / "datamuse_dev6_posthoc.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
