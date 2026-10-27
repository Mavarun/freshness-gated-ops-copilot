#!/usr/bin/env python3
"""One-shot confirm of the seed-free null test -> artifacts/passage_null_pool_confirm.{json,md}.

Reads the chosen q from artifacts/passage_null_pool_calibration.json and applies
``passage_null_pool.confirm_decision`` (pre-registered) to the 20 v2 confirm
traps, the 203-row robustness run and the sweep. Recorded only: the shipped
default on the same traps, its probability over 10,000 control samples of
opening at least one, and both configs on the spent dev6 set. Run once.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ops_copilot.attribute_traps import score_traps  # noqa: E402
from ops_copilot.attribute_traps_v2 import half_v2  # noqa: E402
from ops_copilot.datamuse_dev4 import opened_must_refuse  # noqa: E402
from ops_copilot.passage_null_exact import build_trees, evaluate_sample  # noqa: E402
from ops_copilot.passage_null_pool import config_for, confirm_decision, shipped_config  # noqa: E402
from ops_copilot.robustness import run_robustness  # noqa: E402
from ops_copilot.safety_sweep import sweep  # noqa: E402
from ops_copilot.synonym_dev4 import OPENING  # noqa: E402
from ops_copilot.synonym_dev6 import load_dev6  # noqa: E402
from ops_copilot.wordnet_dev2 import fixed_rows, new_errors, score_rows  # noqa: E402

N_SAMPLES, RNG = 10_000, 20261027


def _rob(cfg) -> dict:
    d = run_robustness(config=cfg).as_dict(flip_detail=True)
    return {k: d[k] for k in ("clean_accuracy", "perturbed_accuracy", "n_perturbed", "per_synonym_split",
                              "n_fail_open", "n_spurious_write", "n_raw_pii_outputs")} | {
        "flips": dict(sorted((f["id"], f["perturbed_decision"]) for f in d["flips"]))}


def _pub(s: dict) -> dict:
    return {k: v for k, v in s.items() if k != "ok"}


def write_md(out: dict, path: Path) -> list[str]:
    lines = ["# Seed-free null test: one-shot confirm (pre-registered, `passage_null_pool.py`)", ""]
    if not out["candidate"]:
        lines.append("No calibration candidate: confirm rows not run.")
    else:
        t, r, d6 = out["traps_v2_confirm"], out["robustness"], out["dev6_spent_recorded_only"]
        hs, hp = r["shipped"]["per_synonym_split"]["heldout"], r["pool"]["per_synonym_split"]["heldout"]
        so = t["shipped_over_samples"]
        lines += [
            f"Arm: whole-pool percentile, q = {out['chosen']['null_min']:.2f}, sticky. "
            "Baseline: the shipped default (seed-42 sample, q = 0.30).", "",
            "| rows (never seen while designing) | shipped default | pool arm |",
            "| :--- | ---: | ---: |",
            f"| v2 confirm traps opened | {t['shipped']['n_opened']}/20 ({', '.join(t['shipped']['opened']) or '-'}) | "
            f"{t['pool']['n_opened']}/20 ({', '.join(t['pool']['opened']) or '-'}) |",
            f"| 203-row clean / perturbed | {r['shipped']['clean_accuracy']:.3f} / {r['shipped']['perturbed_accuracy']:.3f} | "
            f"{r['pool']['clean_accuracy']:.3f} / {r['pool']['perturbed_accuracy']:.3f} |",
            f"| held-out accuracy / ANSWER | {hs['perturbed_accuracy']:.3f} / {hs['by_gate']['ANSWER']['correct']} | "
            f"{hp['perturbed_accuracy']:.3f} / {hp['by_gate']['ANSWER']['correct']} |",
            f"| dev6 (spent, recorded only) correct / ANSWER | {d6['shipped']['correct']}/45 / {d6['shipped']['answer_correct']} | "
            f"{d6['pool']['correct']}/45 / {d6['pool']['answer_correct']} |", "",
            f"Shipped default over {so['n_samples']:,} control samples: P(at least one v2 confirm trap opens) = "
            f"{so['p_at_least_one_open']:.3f} ({so['n_rows_reaching_null_test']} of 20 rows reach the null test).", "",
            "Checks: " + ", ".join(f"{k} {'pass' if v else '**FAIL**'}" for k, v in out["decision"]["checks"].items()) + ".", "",
        ]
    lines.append(f"**Default on: {'yes' if out['decision']['default_on'] else 'no'}.**")
    lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")
    return lines


def main() -> int:
    art = ROOT / "artifacts"
    cal = json.loads((art / "passage_null_pool_calibration.json").read_text())
    out: dict = {"candidate": cal["candidate"]}
    if not cal["candidate"]:
        out["decision"] = {"default_on": False, "reason": "no calibration candidate; confirm rows not run"}
    else:
        chosen = {k: cal["chosen"][k] for k in ("null_min", "pool", "sticky")}
        out["chosen"] = chosen
        base_cfg, on_cfg = shipped_config(), config_for(chosen)
        traps = half_v2("confirm")
        base_t, on_t = score_traps(base_cfg, traps), score_traps(on_cfg, traps)
        trees, pool = build_trees(traps, base_cfg)
        rng = np.random.default_rng(RNG)
        n_open = np.array([sum(d in OPENING for d in evaluate_sample(trees, rng.choice(len(pool), 100, replace=False)).values())
                           for _ in range(N_SAMPLES)])
        base_r, on_r = _rob(base_cfg), _rob(on_cfg)
        sw = sweep(on_cfg, base=base_cfg)
        dev6 = load_dev6()
        d_b, d_o = score_rows(base_cfg, dev6), score_rows(on_cfg, dev6)
        out["traps_v2_confirm"] = {
            "shipped": _pub(base_t), "pool": _pub(on_t),
            "shipped_over_samples": {"n_samples": N_SAMPLES, "rng_seed": RNG,
                                     "n_rows_reaching_null_test": sum(t.decision is None for t in trees.values()),
                                     "p_at_least_one_open": float(np.mean(n_open > 0)),
                                     "mean_opened": float(np.mean(n_open))},
        }
        out["robustness"] = {"shipped": base_r, "pool": on_r,
                             "changed": sorted(set(base_r["flips"].items()) ^ set(on_r["flips"].items()))}
        out["sweep"] = {"n_queries": sw["n_queries"], "changed": sw["changed"], "n_opened": sw["n_opened"],
                        "labelled_trap_opened": [c["query"] for c in sw["labelled_trap_opened"]]}
        out["dev6_spent_recorded_only"] = {
            "shipped": {k: d_b[k] for k in ("correct", "answer_correct", "n", "n_answer")},
            "pool": {k: d_o[k] for k in ("correct", "answer_correct", "n", "n_answer")},
            "fixed": fixed_rows(d_b, d_o), "new_errors": new_errors(d_b, d_o),
            "must_refuse_opened": opened_must_refuse(d_o, dev6)}
        out["decision"] = confirm_decision(on_t, base_r, on_r, sw)
    (art / "passage_null_pool_confirm.json").write_text(json.dumps(out, indent=1, sort_keys=True) + "\n")
    print("\n".join(write_md(out, art / "passage_null_pool_confirm.md")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
