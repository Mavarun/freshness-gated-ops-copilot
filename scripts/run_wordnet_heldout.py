#!/usr/bin/env python3
"""One-shot held-out go / no-go for the WordNet noun-sense read backoff.

Arms (fixed before this run):
- ``off``: the default config;
- ``chosen``: the dev-calibrated gate (artifacts/wordnet_sense_calibration.json),
  the only arm the decision is taken on;
- ``reference_*``: the two looser safe settings (path 1; path 2, fan-out 25).
  Dev could not tell the safe settings apart, so these are reported to show
  what the resource can reach. They are *not* candidates: picking one because
  of this run would be selection on held-out.

Pre-registered rule for default-on: held-out accuracy and held-out ANSWER
rows do not fall, nothing fails open, no spurious write or raw PII, clean
stays 1.000; and (standing rule) the flag must actually improve held-out,
otherwise it ships off. Writes artifacts/wordnet_sense_heldout.json.
"""
from __future__ import annotations

import json
import sys
from dataclasses import replace
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ops_copilot.config import CopilotConfig  # noqa: E402
from ops_copilot.robustness import run_robustness  # noqa: E402


def summarise(cfg: CopilotConfig) -> dict:
    d = run_robustness(config=cfg).as_dict(flip_detail=True)
    flips = {f["id"]: f["perturbed_decision"] for f in d["flips"]}
    return {
        "clean_accuracy": d["clean_accuracy"],
        "perturbed_accuracy": d["perturbed_accuracy"],
        "per_synonym_split": d["per_synonym_split"],
        "n_fail_open": d["n_fail_open"],
        "n_spurious_write": d["n_spurious_write"],
        "n_raw_pii_outputs": d["n_raw_pii_outputs"],
        "flips": dict(sorted(flips.items())),
    }


def go(off: dict, on: dict) -> bool:
    ho, hn = off["per_synonym_split"]["heldout"], on["per_synonym_split"]["heldout"]
    return (
        on["clean_accuracy"] == 1.0
        and hn["perturbed_accuracy"] >= ho["perturbed_accuracy"]
        and hn["by_gate"]["ANSWER"]["correct"] >= ho["by_gate"]["ANSWER"]["correct"]
        and on["n_fail_open"] == 0
        and on["n_spurious_write"] == 0
        and on["n_raw_pii_outputs"] == 0
    )


def main() -> int:
    chosen = json.loads((ROOT / "artifacts" / "wordnet_sense_calibration.json").read_text())["chosen"]
    base = CopilotConfig()
    arms = {
        "chosen": dict(scope=chosen["scope"], path=chosen["max_path"], fan=chosen["max_fanout"],
                       n=chosen["max_neighbours"]),
        "reference_path1": dict(scope="known", path=1, fan=0, n=1),
        "reference_path2_fan25": dict(scope="known", path=2, fan=25, n=1),
    }
    out = {"off": summarise(replace(base, use_wordnet_noun_sense=False))}
    for name, a in arms.items():
        cfg = replace(
            base,
            use_wordnet_noun_sense=True,
            wordnet_scope=a["scope"],
            wordnet_max_path=a["path"],
            wordnet_max_fanout=a["fan"],
            wordnet_max_neighbours=a["n"],
        )
        out[name] = {"setting": a, **summarise(cfg)}
        out[name]["changed_vs_off"] = sorted(
            set(out["off"]["flips"].items()) ^ set(out[name]["flips"].items())
        )
    no_harm = go(out["off"], out["chosen"])
    helps = bool(out["chosen"]["changed_vs_off"]) and (
        out["chosen"]["per_synonym_split"]["heldout"]["perturbed_accuracy"]
        > out["off"]["per_synonym_split"]["heldout"]["perturbed_accuracy"]
    )
    # Standing rule (README): a flag that does not help held-out ships off,
    # even when it does no harm.
    out["decision"] = {
        "decided_on": "chosen",
        "no_harm_rule_passed": no_harm,
        "heldout_gain": helps,
        "default_on": no_harm and helps,
    }
    p = ROOT / "artifacts" / "wordnet_sense_heldout.json"
    p.write_text(json.dumps(out, indent=2, sort_keys=True) + "\n")
    for k in ("off", *arms):
        h = out[k]["per_synonym_split"]["heldout"]
        print(k, out[k]["clean_accuracy"], round(out[k]["perturbed_accuracy"], 4),
              round(h["perturbed_accuracy"], 3), h["by_gate"]["ANSWER"], out[k]["n_fail_open"],
              out[k]["n_spurious_write"], out[k]["n_raw_pii_outputs"], out[k].get("changed_vs_off"))
    print(out["decision"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
