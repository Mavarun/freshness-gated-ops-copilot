#!/usr/bin/env python3
"""One-shot confirm run for the dev2-chosen Datamuse ml gate -> artifacts/datamuse_dev2_confirm.json.

Reads the chosen setting from artifacts/datamuse_dev2_calibration.json. Arms:
flag off vs the chosen setting only. Scores the 21 dev2 confirm rows and the
203-row robustness set (clean, held-out no-harm), and the fresh everyday set
for the record. The rule is ``ops_copilot.wordnet_dev2.confirm_decision``
(unchanged; see ``ops_copilot.datamuse_dev2``).
If calibration found no candidate, nothing is run and the flag ships off.
"""

from __future__ import annotations

import json
import sys
from dataclasses import replace
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ops_copilot.config import CopilotConfig  # noqa: E402
from ops_copilot.fresh_synonym_eval import load_fresh, score as fresh_score  # noqa: E402
from ops_copilot.robustness import run_robustness  # noqa: E402
from ops_copilot.synonym_dev2 import half  # noqa: E402
from ops_copilot.datamuse_dev2 import config_for  # noqa: E402
from ops_copilot.wordnet_dev2 import (  # noqa: E402
    confirm_decision,
    fixed_rows,
    new_errors,
    score_rows,
)


def _rob(cfg: CopilotConfig) -> dict:
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


def main() -> int:
    cal = json.loads((ROOT / "artifacts" / "datamuse_dev2_calibration.json").read_text())
    out: dict = {"chosen": {k: cal["chosen"][k] for k in
                            ("scope", "max_rank", "max_neighbours", "noun_only")},
                 "candidate": cal["candidate"]}
    if not cal["candidate"]:
        out["decision"] = {"default_on": False, "reason": "no calibration candidate; confirm rows not run"}
    else:
        off_cfg = replace(CopilotConfig(), use_datamuse_ml=False)
        on_cfg = config_for(out["chosen"])
        rows = half("confirm")
        off_c, on_c = score_rows(off_cfg, rows), score_rows(on_cfg, rows)
        off_r, on_r = _rob(off_cfg), _rob(on_cfg)
        fresh = load_fresh()
        out["confirm"] = {
            "off": {k: v for k, v in off_c.items() if k != "ok"},
            "on": {k: v for k, v in on_c.items() if k != "ok"},
            "fixed": fixed_rows(off_c, on_c),
            "new_errors": new_errors(off_c, on_c),
        }
        out["robustness"] = {"off": off_r, "on": on_r,
                             "changed_vs_off": sorted(set(off_r["flips"].items()) ^ set(on_r["flips"].items()))}
        out["fresh"] = {"off": fresh_score(off_cfg, fresh), "on": fresh_score(on_cfg, fresh)}
        out["decision"] = confirm_decision(off_c, on_c, off_r, on_r)
    (ROOT / "artifacts" / "datamuse_dev2_confirm.json").write_text(json.dumps(out, indent=2, sort_keys=True) + "\n")
    print(json.dumps({k: out[k] for k in ("chosen", "decision")}, indent=1))
    if "confirm" in out:
        for arm in ("off", "on"):
            c, r = out["confirm"][arm], out["robustness"][arm]
            h = r["per_synonym_split"]["heldout"]
            print(arm, "confirm", f"{c['correct']}/{c['n']}", "ANSWER", f"{c['answer_correct']}/{c['n_answer']}",
                  "| clean", r["clean_accuracy"], "perturbed", round(r["perturbed_accuracy"], 4),
                  "heldout", round(h["perturbed_accuracy"], 3), h["by_gate"]["ANSWER"],
                  "| fresh", round(out["fresh"][arm]["accuracy"], 3), out["fresh"][arm]["answer_correct"])
        print("fixed", out["confirm"]["fixed"], "new errors", out["confirm"]["new_errors"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
