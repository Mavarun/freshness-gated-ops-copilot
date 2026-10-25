#!/usr/bin/env python3
"""Post-hoc: why the null-control test cannot both close the traps and keep the rescues.

-> artifacts/passage_null_diagnosis.{json,md}. Selects nothing.

For every calibration row (dev5 calibration, 171) and attribute-trap tune row
(18) whose shipped-default decision depends on the passage rescue (it
changes when ``use_passage_support_model`` is off), this records, on the
evidence part of the final grounding call: the classifier logit of the real
query, the median logit over the 100 seeded controls substituted for the
rescued word, and their difference (``margin``). ``keep`` rows are correct
in the shipped default and wrong without the rescue; ``trap`` rows are
attribute traps or must-refuse rows the rescue opens. Dev5 confirm, the trap
confirm half and held-out rows are never scored.
"""

from __future__ import annotations

import json
import sys
from dataclasses import replace
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ops_copilot.attribute_traps import half as trap_half  # noqa: E402
from ops_copilot.datamuse_dev5 import calibration_rows  # noqa: E402
from ops_copilot.passage_null_dev5 import pre_change_config  # noqa: E402
from ops_copilot.pipeline import Copilot  # noqa: E402
from ops_copilot.qa_translation import words as qa_words  # noqa: E402
from ops_copilot.synonym_dev4 import OPENING  # noqa: E402
from ops_copilot.text import fold_token, is_identifier  # noqa: E402


def main() -> int:
    base = Copilot(config=pre_change_config())
    off = Copilot(config=replace(pre_change_config(), use_passage_support_model=False))
    g = Copilot(config=replace(pre_change_config(), passage_support_null_min=0.1)).grounder
    controls, model = g.passage_null_controls, g.passage_support
    last: dict[str, tuple] = {}
    orig = base.grounder.passage_rescue

    def spy(query, terms, covered, parts):
        out, p = orig(query, terms, covered, parts)
        if out:
            last[query] = (out, parts, terms)
        return out, p

    base.grounder.passage_rescue = spy
    rows = calibration_rows() + [{**r, "set": "traps_tune"} for r in trap_half("tune")]
    recs = []
    for r in rows:
        a = base.ask(r["query"])
        if not (a.grounding and a.grounding.passage_rescued) or r["query"] not in last:
            continue
        b = off.ask(r["query"])
        if a.decision == b.decision:
            continue
        got, want = a.decision.value, r["expect_decision"]
        if got == want:
            kind = "keep"
        elif want not in OPENING and got in OPENING:
            kind = "trap"
        else:
            continue  # wrong either way or a refusal of another type: not informative
        out, parts, terms = last[r["query"]]
        t = out[0]
        qw = [fold_token(x.token) for x in terms if x.token.isalpha() and not is_identifier(x.token)]
        verdicts = [(model.verdict(qw, qa_words(p), g._plain_weight), qa_words(p)) for p in parts]
        v, pw = max(verdicts, key=lambda x: x[0].prob)
        word = fold_token(t.query_word)

        def logit(q):
            return model.classifier.logit(model.verdict(q, pw, g._plain_weight).features)

        real = logit(qw)
        ctrl = np.array([logit([c if w == word else w for w in qw]) for c in controls])
        recs.append({
            "id": r["id"], "set": r["set"], "kind": kind, "expect": want, "rescue": f"{t.query_word}<-{t.evidence_word}",
            "logit": round(real, 3), "control_median": round(float(np.median(ctrl)), 3),
            "margin": round(real - float(np.median(ctrl)), 3),
        })
    # Why q = 0.5 still opens two traps: the rescue is tried once per
    # supporting chunk (retrieval) and once on the final evidence, and one
    # passing chunk is enough. Record the per-call percentiles.
    from ops_copilot import grounding as G

    strict = Copilot(config=replace(pre_change_config(), passage_support_null_min=0.5))
    calls: list[float] = []
    real_pct = G.null_percentile

    def spy_pct(*args, **kw):
        pct = real_pct(*args, **kw)
        calls.append(round(pct, 2))
        return pct

    G.null_percentile = spy_pct
    per_call = {}
    try:
        for r in trap_half("tune"):
            calls.clear()
            res = strict.ask(r["query"])
            if res.decision.value in OPENING:
                per_call[r["id"]] = {"decision": res.decision.value, "call_percentiles": list(calls),
                                     "rescue": res.grounding.passage_rescued}
    finally:
        G.null_percentile = real_pct
    traps = [x for x in recs if x["kind"] == "trap"]
    keeps = [x for x in recs if x["kind"] == "keep"]
    worst_trap = max(x["margin"] for x in traps)
    below = [x for x in keeps if x["margin"] <= worst_trap]
    rep = {
        "post_hoc": True,
        "n_controls": len(controls),
        "n_keep": len(keeps),
        "n_trap": len(traps),
        "trap_margin_max": worst_trap,
        "keep_at_or_below_trap_max": [x["id"] for x in below],
        "keep_answer_at_or_below_trap_max": [x["id"] for x in below if x["expect"] == "ANSWER"],
        "keep_below_zero": [x["id"] for x in keeps if x["margin"] < 0],
        "rows": recs,
        "open_at_q050_per_call": per_call,
    }
    art = ROOT / "artifacts"
    (art / "passage_null_diagnosis.json").write_text(json.dumps(rep, indent=2, sort_keys=True) + "\n")
    lines = [
        "# Null-control margins on rescue-dependent rows (post-hoc, selects nothing)",
        "",
        f"{len(keeps)} keep rows (correct only with the rescue) and {len(traps)} trap rows "
        "(a must-refuse or attribute-trap row the rescue opens), final grounding call, 100 controls.",
        "",
        "| id | kind | rescue | logit | control median | margin |",
        "| :--- | :--- | :--- | ---: | ---: | ---: |",
    ]
    for x in sorted(recs, key=lambda x: x["margin"]):
        lines.append(f"| {x['id']} | {x['kind']} | `{x['rescue']}` | {x['logit']:.2f} | {x['control_median']:.2f} | "
                     f"{x['margin']:+.2f} |")
    lines += [
        "",
        f"Every trap scores below its control median (max margin {worst_trap:+.2f}), so the real word "
        "adds nothing over an unrelated one. But {n} keep rows score at or below that too ({ids}), "
        "{a} of them ANSWER rows. Their rescues are topical as well: the passage answers the question "
        "whatever the missing word is.".format(n=len(below), ids=", ".join(x["id"] for x in below),
                                                a=len(rep["keep_answer_at_or_below_trap_max"])),
        "",
        "Still open at q = 0.50, percentile per rescue attempt (each supporting chunk, then the final evidence):",
        "",
    ]
    for rid, x in sorted(per_call.items()):
        lines.append(f"- {rid}: {x['call_percentiles']} -> {x['decision']} via `{', '.join(x['rescue'])}`")
    lines += [
        "",
        "One chunk below the bar is not enough: another chunk passes and the answer goes through it.",
        "",
    ]
    (art / "passage_null_diagnosis.md").write_text("\n".join(lines))
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
