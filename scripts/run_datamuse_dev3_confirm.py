#!/usr/bin/env python3
"""One-shot confirm for the dev3-chosen context-gated Datamuse arm -> artifacts/datamuse_dev3_confirm.json.

Reads the chosen setting from artifacts/datamuse_dev3_calibration.json. The
decision compares flag off vs the chosen setting only, on the 20 dev3 confirm
rows and the 203-row robustness run, by ``wordnet_dev2.confirm_decision``
(unchanged). Recorded, never used to decide: the shelved dev2-chosen WordNet
and Datamuse arms on the same rows, and every arm on the fresh everyday set.
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
from ops_copilot.datamuse_dev2 import config_for as dev2_datamuse_config  # noqa: E402
from ops_copilot.datamuse_dev3 import config_for  # noqa: E402
from ops_copilot.fresh_synonym_eval import load_fresh, score as fresh_score  # noqa: E402
from ops_copilot.robustness import run_robustness  # noqa: E402
from ops_copilot.synonym_dev3 import half  # noqa: E402
from ops_copilot.wordnet_dev2 import config_for as wordnet_config  # noqa: E402
from ops_copilot.wordnet_dev2 import confirm_decision, fixed_rows, new_errors, score_rows  # noqa: E402

KNOBS = ("scope", "max_rank", "max_neighbours", "context_min")


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


def _pub(s: dict) -> dict:
    return {k: v for k, v in s.items() if k != "ok"}


def main() -> int:
    art = ROOT / "artifacts"
    cal = json.loads((art / "datamuse_dev3_calibration.json").read_text())
    out: dict = {"chosen": {k: cal["chosen"][k] for k in KNOBS}, "candidate": cal["candidate"]}
    if not cal["candidate"]:
        out["decision"] = {"default_on": False, "reason": "no calibration candidate; confirm rows not run"}
    else:
        rows = half("confirm")
        off_cfg = replace(CopilotConfig(), use_datamuse_ml=False)
        on_cfg = config_for(out["chosen"])
        refs = {
            "wordnet_dev2_chosen": wordnet_config(json.loads((art / "wordnet_dev2_confirm.json").read_text())["chosen"]),
            "datamuse_dev2_chosen": dev2_datamuse_config(
                json.loads((art / "datamuse_dev2_confirm.json").read_text())["chosen"]),
        }
        off_c, on_c = score_rows(off_cfg, rows), score_rows(on_cfg, rows)
        off_r, on_r = _rob(off_cfg), _rob(on_cfg)
        fresh = load_fresh()
        out["confirm"] = {
            "off": _pub(off_c), "on": _pub(on_c),
            "fixed": fixed_rows(off_c, on_c), "new_errors": new_errors(off_c, on_c),
        }
        out["robustness"] = {"off": off_r, "on": on_r,
                             "changed_vs_off": sorted(set(off_r["flips"].items()) ^ set(on_r["flips"].items()))}
        out["fresh"] = {"off": fresh_score(off_cfg, fresh), "on": fresh_score(on_cfg, fresh)}
        out["reference_arms"] = {}
        for name, cfg in refs.items():
            rc = score_rows(cfg, rows)
            out["reference_arms"][name] = {
                "confirm": _pub(rc), "fixed": fixed_rows(off_c, rc), "new_errors": new_errors(off_c, rc),
                "fresh": fresh_score(cfg, fresh),
            }
        out["decision"] = confirm_decision(off_c, on_c, off_r, on_r)
    (art / "datamuse_dev3_confirm.json").write_text(json.dumps(out, indent=2, sort_keys=True) + "\n")
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
        for name, ref in out["reference_arms"].items():
            print(name, f"{ref['confirm']['correct']}/{ref['confirm']['n']}", "ANSWER",
                  ref["confirm"]["answer_correct"], "new errors", ref["new_errors"],
                  "| fresh", round(ref["fresh"]["accuracy"], 3), ref["fresh"]["answer_correct"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
