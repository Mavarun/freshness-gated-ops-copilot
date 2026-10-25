#!/usr/bin/env python3
"""One-shot confirm of the v2-chosen null-control test -> artifacts/passage_null_confirm.json.

Reads the chosen setting from artifacts/passage_null_v2_calibration.json and
compares it with the shipped default on the 20 dev5 confirm rows, the 18
attribute-trap confirm rows (attributes never seen while designing), the
203-row robustness run (held-out) and the tests/ sweep. The decision is
``passage_null_dev5.confirm_decision``, pre-registered before any of these
rows was scored. Run once; the committed artifact is the record.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ops_copilot.attribute_traps import half as trap_half, score_traps  # noqa: E402
from ops_copilot.config import CopilotConfig  # noqa: E402
from ops_copilot.datamuse_dev4 import opened_must_refuse  # noqa: E402
from ops_copilot.passage_null_dev5 import config_for, confirm_decision  # noqa: E402
from ops_copilot.robustness import run_robustness  # noqa: E402
from ops_copilot.safety_sweep import sweep  # noqa: E402
from ops_copilot.synonym_dev5 import half  # noqa: E402
from ops_copilot.wordnet_dev2 import fixed_rows, new_errors, score_rows  # noqa: E402


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
    cal = json.loads((art / "passage_null_v2_calibration.json").read_text())
    chosen = {k: cal["chosen"][k] for k in ("null_min", "sticky")}
    out: dict = {"chosen": chosen, "candidate": cal["candidate"]}
    if not cal["candidate"]:
        out["decision"] = {"default_on": False, "reason": "no calibration candidate; confirm rows not run"}
    else:
        rows, traps = half("confirm"), trap_half("confirm")
        off_cfg, on_cfg = CopilotConfig(), config_for(chosen)
        off_c, on_c = score_rows(off_cfg, rows), score_rows(on_cfg, rows)
        off_t, on_t = score_traps(off_cfg, traps), score_traps(on_cfg, traps)
        off_r, on_r = _rob(off_cfg), _rob(on_cfg)
        sw = sweep(on_cfg)
        out["dev5_confirm"] = {
            "off": _pub(off_c), "on": _pub(on_c),
            "fixed": fixed_rows(off_c, on_c), "new_errors": new_errors(off_c, on_c),
            "must_refuse_rows": sum(r["expect_decision"].startswith("REFUSE_") for r in rows),
            "must_refuse_opened_off": opened_must_refuse(off_c, rows),
            "must_refuse_opened_on": opened_must_refuse(on_c, rows),
        }
        out["traps_confirm"] = {"off": off_t, "on": on_t}
        out["robustness"] = {"off": off_r, "on": on_r,
                             "changed_vs_off": sorted(set(off_r["flips"].items()) ^ set(on_r["flips"].items()))}
        out["sweep"] = {"n_queries": sw["n_queries"], "changed": sw["changed"], "n_opened": sw["n_opened"],
                        "labelled_trap_opened": [c["query"] for c in sw["labelled_trap_opened"]]}
        out["decision"] = confirm_decision(off_c, on_c, rows, on_t, off_r, on_r, sw)
    (art / "passage_null_confirm.json").write_text(json.dumps(out, indent=2, sort_keys=True) + "\n")
    print(json.dumps({k: out[k] for k in ("chosen", "decision")}, indent=2))
    if "dev5_confirm" in out:
        c, t, r = out["dev5_confirm"], out["traps_confirm"], out["robustness"]
        print("dev5 confirm off/on", c["off"]["correct"], c["on"]["correct"], "of", c["off"]["n"],
              "ANSWER", c["off"]["answer_correct"], c["on"]["answer_correct"], "of", c["off"]["n_answer"],
              "opened", c["must_refuse_opened_off"], c["must_refuse_opened_on"], "fixed", c["fixed"], "new", c["new_errors"])
        print("traps confirm opened off/on", t["off"]["opened"], t["on"]["opened"])
        for k in ("off", "on"):
            h = r[k]["per_synonym_split"]["heldout"]
            print(k, "clean", r[k]["clean_accuracy"], "perturbed", round(r[k]["perturbed_accuracy"], 4), "heldout",
                  round(h["perturbed_accuracy"], 4), "ANSWER", h["by_gate"]["ANSWER"], "fail-open", r[k]["n_fail_open"])
        print("robustness changed", r["changed_vs_off"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
