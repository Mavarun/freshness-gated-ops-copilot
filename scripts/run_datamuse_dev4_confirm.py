#!/usr/bin/env python3
"""One-shot confirm for the dev4-chosen unknown-words-only Datamuse arm -> artifacts/datamuse_dev4_confirm.json.

Reads the chosen setting from artifacts/datamuse_dev4_calibration.json. The
decision (``datamuse_dev4.confirm_decision``) compares flag off vs the chosen
setting only, on the 21 dev4 confirm rows, the 203-row robustness run
(held-out as no-harm only) and the tests/ literal sweep. Recorded, never used
to decide: the dev3-chosen arm (expands known words; ships off) and the dev3
post-hoc unknown-only arm on the same rows, and every arm on the fresh set.
If calibration found no candidate, nothing is run and the flag ships off.
"""

from __future__ import annotations

import json
import sys
from dataclasses import replace
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ops_copilot.datamuse_dev3 import config_for as dev3_config  # noqa: E402
from ops_copilot.datamuse_dev4 import config_for, confirm_decision, off_config, opened_must_refuse  # noqa: E402
from ops_copilot.fresh_synonym_eval import load_fresh, score as fresh_score  # noqa: E402
from ops_copilot.robustness import run_robustness  # noqa: E402
from ops_copilot.safety_sweep import sweep  # noqa: E402
from ops_copilot.synonym_dev4 import half  # noqa: E402
from ops_copilot.wordnet_dev2 import fixed_rows, new_errors, score_rows  # noqa: E402

KNOBS = ("max_rank", "max_neighbours", "context_min")


def _rob(cfg) -> dict:
    d = run_robustness(config=cfg).as_dict(flip_detail=True)
    return {
        "clean_accuracy": d["clean_accuracy"],
        "perturbed_accuracy": d["perturbed_accuracy"],
        "per_synonym_split": d["per_synonym_split"],
        "n_fail_open": d["n_fail_open"],
        "n_spurious_write": d["n_spurious_write"],
        "n_raw_pii_outputs": d["n_raw_pii_outputs"],
        "flips": dict(sorted((f["id"], f["perturbed_decision"]) for f in d["flips"])),
    }


def _pub(s: dict) -> dict:
    return {k: v for k, v in s.items() if k != "ok"}


def main() -> int:
    art = ROOT / "artifacts"
    cal = json.loads((art / "datamuse_dev4_calibration.json").read_text())
    out: dict = {"chosen": {k: cal["chosen"][k] for k in KNOBS}, "candidate": cal["candidate"]}
    if not cal["candidate"]:
        out["decision"] = {"default_on": False, "reason": "no calibration candidate; confirm rows not run"}
    else:
        rows = half("confirm")
        off_cfg, on_cfg = off_config(), config_for(out["chosen"])
        d3_chosen = json.loads((art / "datamuse_dev3_confirm.json").read_text())["chosen"]
        refs = {
            "dev3_chosen_expands_known": dev3_config(d3_chosen),
            "dev3_posthoc_unknown_only": replace(dev3_config(d3_chosen), datamuse_expand_known=False),
        }
        off_c, on_c = score_rows(off_cfg, rows), score_rows(on_cfg, rows)
        off_r, on_r = _rob(off_cfg), _rob(on_cfg)
        sw = sweep(on_cfg)
        fresh = load_fresh()
        out["confirm"] = {
            "off": _pub(off_c), "on": _pub(on_c),
            "fixed": fixed_rows(off_c, on_c), "new_errors": new_errors(off_c, on_c),
            "must_refuse_rows": len([r for r in rows if r["expect_decision"].startswith("REFUSE_")]),
            "must_refuse_opened_off": opened_must_refuse(off_c, rows),
            "must_refuse_opened_on": opened_must_refuse(on_c, rows),
        }
        out["robustness"] = {"off": off_r, "on": on_r,
                             "changed_vs_off": sorted(set(off_r["flips"].items()) ^ set(on_r["flips"].items()))}
        out["sweep"] = {"n_queries": sw["n_queries"], "changed": sw["changed"], "n_opened": sw["n_opened"],
                        "labelled_trap_opened": [c["query"] for c in sw["labelled_trap_opened"]]}
        out["fresh"] = {"off": fresh_score(off_cfg, fresh), "on": fresh_score(on_cfg, fresh)}
        out["reference_arms"] = {}
        for name, cfg in refs.items():
            rc = score_rows(cfg, rows)
            out["reference_arms"][name] = {
                "confirm": _pub(rc), "fixed": fixed_rows(off_c, rc), "new_errors": new_errors(off_c, rc),
                "must_refuse_opened": opened_must_refuse(rc, rows), "fresh": fresh_score(cfg, fresh),
            }
        out["decision"] = confirm_decision(off_c, on_c, off_r, on_r, rows, sw)
    (art / "datamuse_dev4_confirm.json").write_text(json.dumps(out, indent=2, sort_keys=True) + "\n")
    print(json.dumps({k: out[k] for k in ("chosen", "decision")}, indent=1))
    if "confirm" in out:
        for arm in ("off", "on"):
            c, r = out["confirm"][arm], out["robustness"][arm]
            h = r["per_synonym_split"]["heldout"]
            print(arm, "confirm", f"{c['correct']}/{c['n']}", "ANSWER", f"{c['answer_correct']}/{c['n_answer']}",
                  "| clean", r["clean_accuracy"], "perturbed", round(r["perturbed_accuracy"], 4),
                  "heldout", round(h["perturbed_accuracy"], 3), h["by_gate"]["ANSWER"],
                  "| fresh", round(out["fresh"][arm]["accuracy"], 3), out["fresh"][arm]["answer_correct"])
        print("fixed", out["confirm"]["fixed"], "new errors", out["confirm"]["new_errors"],
              "must-refuse opened", out["confirm"]["must_refuse_opened_on"])
        print("sweep opened", out["sweep"]["n_opened"], "labelled", out["sweep"]["labelled_trap_opened"])
        for name, ref in out["reference_arms"].items():
            print(name, f"{ref['confirm']['correct']}/{ref['confirm']['n']}", "ANSWER",
                  ref["confirm"]["answer_correct"], "new errors", ref["new_errors"],
                  "must-refuse opened", ref["must_refuse_opened"],
                  "| fresh", round(ref["fresh"]["accuracy"], 3), ref["fresh"]["answer_correct"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
