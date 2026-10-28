#!/usr/bin/env python3
"""One-shot confirm of the credited-word check -> artifacts/credit_check_confirm.{json,md}.

Reads the chosen arm from artifacts/credit_check_calibration.json and applies
``credit_check.confirm_decision`` (pre-registered) to the 19 v3 confirm traps,
the 18 dev7 confirm rows, the 203-row robustness run and the sweep. Recorded
only: the shipped default on the same rows, an exact sign test on changed
dev7 confirm rows and the fresh general-English set. Run once.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ops_copilot.attribute_traps import score_traps  # noqa: E402
from ops_copilot.attribute_traps_v3 import half_v3  # noqa: E402
from ops_copilot.credit_check import config_for, confirm_decision, shipped_config  # noqa: E402
from ops_copilot.datamuse_dev6 import sign_test_p  # noqa: E402
from ops_copilot.fresh_synonym_eval import load_fresh, score as fresh_score  # noqa: E402
from ops_copilot.robustness import run_robustness  # noqa: E402
from ops_copilot.safety_sweep import sweep  # noqa: E402
from ops_copilot.synonym_dev7 import half as dev7_half  # noqa: E402
from ops_copilot.wordnet_dev2 import fixed_rows, new_errors, score_rows  # noqa: E402

KEYS = ("stop", "top_freq", "max_rank")


def _rob(cfg) -> dict:
    d = run_robustness(config=cfg).as_dict(flip_detail=True)
    return {k: d[k] for k in ("clean_accuracy", "perturbed_accuracy", "n_perturbed", "per_synonym_split",
                              "n_fail_open", "n_spurious_write", "n_raw_pii_outputs")} | {
        "flips": dict(sorted((f["id"], f["perturbed_decision"]) for f in d["flips"]))}


def _pub(s: dict) -> dict:
    return {k: v for k, v in s.items() if k != "ok"}


def write_md(out: dict, path: Path) -> list[str]:
    lines = ["# Credited-word check: one-shot confirm (pre-registered, `credit_check.py`)", ""]
    if not out["candidate"]:
        lines.append("No calibration candidate: confirm rows not run.")
    else:
        t, d7, r, fr = out["traps_v3_confirm"], out["dev7_confirm"], out["robustness"], out["fresh"]
        hs, hc = (r[a]["per_synonym_split"]["heldout"] for a in ("shipped", "arm"))
        ch = out["chosen"]
        lines += [
            f"Arm: stop={ch['stop']}, top_freq={ch['top_freq']}, max_rank={ch['max_rank']} "
            "on the shipped default (null test seed 42, q = 0.30, sticky).", "",
            "| rows never seen while designing | shipped default | credited-word arm |",
            "| :--- | ---: | ---: |",
            f"| v3 confirm traps opened | {t['shipped']['n_opened']}/19 ({', '.join(t['shipped']['opened']) or '-'}) | "
            f"{t['arm']['n_opened']}/19 ({', '.join(t['arm']['opened']) or '-'}) |",
            f"| dev7 confirm correct / ANSWER | {d7['shipped']['correct']}/18 / {d7['shipped']['answer_correct']} of 13 | "
            f"{d7['arm']['correct']}/18 / {d7['arm']['answer_correct']} of 13 |",
            f"| 203-row clean / perturbed | {r['shipped']['clean_accuracy']:.3f} / {r['shipped']['perturbed_accuracy']:.3f} | "
            f"{r['arm']['clean_accuracy']:.3f} / {r['arm']['perturbed_accuracy']:.3f} |",
            f"| held-out accuracy / ANSWER | {hs['perturbed_accuracy']:.3f} / {hs['by_gate']['ANSWER']['correct']} of "
            f"{hs['by_gate']['ANSWER']['n']} | {hc['perturbed_accuracy']:.3f} / {hc['by_gate']['ANSWER']['correct']} of "
            f"{hc['by_gate']['ANSWER']['n']} |",
            f"| fresh general-English set (recorded) | {fr['shipped']['accuracy']:.3f} ({fr['shipped']['answer_correct']}) | "
            f"{fr['arm']['accuracy']:.3f} ({fr['arm']['answer_correct']}) |", "",
            f"dev7 confirm: fixed {', '.join(d7['fixed']) or 'none'}; new errors {', '.join(d7['new_errors']) or 'none'}; "
            f"exact sign test (recorded only) p = {out['sign_test_p']:.3f}.",
            f"Robustness rows that change: {', '.join(f'{k}->{v}' for k, v in r['changed']) or 'none'}.",
            f"Sweep: {out['sweep']['n_opened']} opened, labelled traps opened: "
            f"{', '.join(out['sweep']['labelled_trap_opened']) or 'none'}.", "",
            "Checks: " + ", ".join(f"{k} {'pass' if v else '**FAIL**'}" for k, v in out["decision"]["checks"].items()) + ".", "",
        ]
    lines.append(f"**Default on: {'yes' if out['decision']['default_on'] else 'no'}.**")
    lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")
    return lines


def main() -> int:
    art = ROOT / "artifacts"
    cal = json.loads((art / "credit_check_calibration.json").read_text())
    out: dict = {"candidate": cal["candidate"]}
    if not cal["candidate"]:
        out["decision"] = {"default_on": False, "reason": "no calibration candidate; confirm rows not run"}
    else:
        chosen = {k: cal["chosen"][k] for k in KEYS}
        out["chosen"] = chosen
        base_cfg, on_cfg = shipped_config(), config_for(chosen)
        traps = half_v3("confirm")
        base_t, on_t = score_traps(base_cfg, traps), score_traps(on_cfg, traps)
        rows = dev7_half("confirm")
        d_b, d_o = score_rows(base_cfg, rows), score_rows(on_cfg, rows)
        base_r, on_r = _rob(base_cfg), _rob(on_cfg)
        sw = sweep(on_cfg, base=base_cfg)
        fresh = load_fresh()
        fx, ne = fixed_rows(d_b, d_o), new_errors(d_b, d_o)
        out["traps_v3_confirm"] = {"shipped": _pub(base_t), "arm": _pub(on_t)}
        out["dev7_confirm"] = {"shipped": _pub(d_b), "arm": _pub(d_o), "fixed": fx, "new_errors": ne}
        out["sign_test_p"] = sign_test_p(len(fx), len(ne))
        out["robustness"] = {"shipped": base_r, "arm": on_r,
                             "changed": sorted(set(on_r["flips"].items()) - set(base_r["flips"].items()))
                             + sorted((k, "fixed") for k in set(base_r["flips"]) - set(on_r["flips"]))}
        out["sweep"] = {"n_queries": sw["n_queries"], "changed": sw["changed"], "n_opened": sw["n_opened"],
                        "labelled_trap_opened": [c["query"] for c in sw["labelled_trap_opened"]]}
        out["fresh"] = {"shipped": fresh_score(base_cfg, fresh), "arm": fresh_score(on_cfg, fresh)}
        out["decision"] = confirm_decision(on_t, d_b, d_o, rows, base_r, on_r, sw)
    (art / "credit_check_confirm.json").write_text(json.dumps(out, indent=1, sort_keys=True) + "\n")
    print("\n".join(write_md(out, art / "credit_check_confirm.md")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
