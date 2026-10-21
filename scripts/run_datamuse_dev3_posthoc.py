#!/usr/bin/env python3
"""Post-hoc (selects nothing): does mapping unknown words only close the sweep's fail-open?

-> artifacts/datamuse_dev3_posthoc.json. Arms: flag off, the dev3-chosen arm,
and the same arm with ``datamuse_expand_known=False``. Scores the calibration
rows, the dev3 confirm rows (already used once, so this is not a confirm),
the 203-row robustness run, the fresh set and the unit-test literal sweep.
Anything learnt here needs a new pre-registered set before it may ship.
"""

from __future__ import annotations

import json
import sys
from dataclasses import replace
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ops_copilot.config import CopilotConfig  # noqa: E402
from ops_copilot.datamuse_dev3 import calibration_rows, config_for  # noqa: E402
from ops_copilot.fresh_synonym_eval import load_fresh, score as fresh_score  # noqa: E402
from ops_copilot.robustness import run_robustness  # noqa: E402
from ops_copilot.safety_sweep import sweep  # noqa: E402
from ops_copilot.synonym_dev3 import half  # noqa: E402
from ops_copilot.wordnet_dev2 import new_errors, score_rows  # noqa: E402


def main() -> int:
    art = ROOT / "artifacts"
    chosen = json.loads((art / "datamuse_dev3_confirm.json").read_text())["chosen"]
    arms = {
        "off": replace(CopilotConfig(), use_datamuse_ml=False),
        "dev3-chosen": config_for(chosen),
        "dev3-chosen, unknown words only": replace(config_for(chosen), datamuse_expand_known=False),
    }
    cal, conf, fresh = calibration_rows(), half("confirm"), load_fresh()
    base = {"calib": score_rows(arms["off"], cal), "confirm": score_rows(arms["off"], conf)}
    out: dict = {"chosen": chosen, "post_hoc": True, "arms": {}}
    for name, cfg in arms.items():
        c, f = score_rows(cfg, cal), score_rows(cfg, conf)
        r = run_robustness(config=cfg).as_dict()
        h = r["per_synonym_split"]["heldout"]
        sw = sweep(cfg) if name != "off" else None
        out["arms"][name] = {
            "calib": f"{c['correct']}/{c['n']}", "calib_new_errors": new_errors(base["calib"], c),
            "confirm": f"{f['correct']}/{f['n']}", "confirm_answer": f"{f['answer_correct']}/{f['n_answer']}",
            "confirm_new_errors": new_errors(base["confirm"], f),
            "clean": r["clean_accuracy"], "perturbed": round(r["perturbed_accuracy"], 4),
            "heldout": round(h["perturbed_accuracy"], 3), "heldout_answer": h["by_gate"]["ANSWER"]["correct"],
            "fail_open": r["n_fail_open"] + c["n_fail_open"] + f["n_fail_open"],
            "fresh": fresh_score(cfg, fresh)["accuracy"],
            "sweep_opened": None if sw is None else sw["n_opened"],
            "sweep_labelled_trap_opened": None if sw is None else [x["query"] for x in sw["labelled_trap_opened"]],
        }
    (art / "datamuse_dev3_posthoc.json").write_text(json.dumps(out, indent=2, sort_keys=True) + "\n")
    print(json.dumps(out["arms"], indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
