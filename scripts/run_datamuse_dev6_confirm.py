#!/usr/bin/env python3
"""One-shot confirm of the frozen word-meaning Datamuse arm on dev6 -> artifacts/datamuse_dev6_confirm.{json,md}.

Protocol: ``ops_copilot/datamuse_dev6.py`` (committed before this ran). Off =
the shipped default; on = the same plus the frozen arm. Scored once on all 45
dev6 rows, the 203-row robustness run (held-out as no-harm only), the tests/
literal sweep and the 36 attribute traps. Recorded, never used to decide: the
exact sign test on changed dev6 rows and the fresh general-English set.
dev6 is spent after this run, whatever the outcome.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ops_copilot.datamuse_dev6 import (  # noqa: E402
    ARM,
    arm_config,
    confirm_decision,
    off_config,
    opened_must_refuse,
    score_attribute_traps,
    sign_test_p,
)
from ops_copilot.fresh_synonym_eval import load_fresh, score as fresh_score  # noqa: E402
from ops_copilot.robustness import run_robustness  # noqa: E402
from ops_copilot.safety_sweep import sweep  # noqa: E402
from ops_copilot.synonym_dev6 import load_dev6, must_refuse_rows  # noqa: E402
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


def _fc(f: dict) -> str:
    return f"{f['n'] - len(f['wrong'])}/{f['n']}"


def _md(out: dict, rows: list[dict]) -> str:
    c, r, dec = out["confirm"], out["robustness"], out["decision"]
    q = {x["id"]: x["query"] for x in rows}
    fixed = ", ".join(f"{i} ({q[i]})" for i in c["fixed"])
    broken = ", ".join(f"{i} ({q[i]} -> {c['on']['decisions'][i]})" for i in c["new_errors"])
    lines = [
        "# Word-meaning Datamuse arm: one-shot confirm on dev6 (pre-registered, `datamuse_dev6.py`)", "",
        f"Arm: rank<={ARM['max_rank']} n{ARM['max_neighbours']} context>={ARM['context_min']} "
        f"sense>={ARM['sense_min']:.2f}, on top of the shipped default. 45 dev6 rows "
        f"({c['must_refuse_rows']} must-refuse), the 203-row run, the tests/ sweep and 36 attribute traps.", "",
        "| | shipped default | + Datamuse arm |", "| :--- | ---: | ---: |",
        f"| dev6 correct | {c['off']['correct']}/{c['off']['n']} | {c['on']['correct']}/{c['on']['n']} |",
        f"| dev6 ANSWER | {c['off']['answer_correct']}/{c['off']['n_answer']} | "
        f"{c['on']['answer_correct']}/{c['on']['n_answer']} |",
        f"| dev6 must-refuse opened | {', '.join(c['must_refuse_opened_off']) or '0'} | "
        f"{', '.join(c['must_refuse_opened_on']) or '0'} |",
    ]
    ho, hn = (r[a]["per_synonym_split"]["heldout"] for a in ("off", "on"))
    lines += [
        f"| 203-row clean / perturbed | {r['off']['clean_accuracy']:.3f} / {r['off']['perturbed_accuracy']:.3f} | "
        f"{r['on']['clean_accuracy']:.3f} / {r['on']['perturbed_accuracy']:.3f} |",
        f"| held-out accuracy / ANSWER | {ho['perturbed_accuracy']:.3f} / {ho['by_gate']['ANSWER']['correct']} of "
        f"{ho['by_gate']['ANSWER']['n']} | {hn['perturbed_accuracy']:.3f} / {hn['by_gate']['ANSWER']['correct']} of "
        f"{hn['by_gate']['ANSWER']['n']} |",
        f"| attribute traps opened | {out['traps']['off']['n_opened']}/36 | {out['traps']['on']['n_opened']}/36 |",
        f"| fresh general-English set | {_fc(out['fresh']['off'])} | {_fc(out['fresh']['on'])} |",
        "",
        f"Fixed: {fixed or 'none'}.",
        f"New errors: {broken or 'none'}.",
        f"Sweep: {out['sweep']['n_opened']} opened, labelled traps opened: "
        f"{', '.join(out['sweep']['labelled_trap_opened']) or 'none'}.",
        f"Exact sign test on changed dev6 rows (recorded only): {len(c['fixed'])} fixed vs "
        f"{len(c['new_errors'])} broken, p = {out['sign_test_p']:.3f}.", "",
        "| check | pass |", "| :--- | :---: |",
        *[f"| {k} | {'yes' if v else '**no**'} |" for k, v in dec["checks"].items()], "",
        f"**Decision: {'default on' if dec['default_on'] else 'ships off'}.** dev6 is now spent.",
    ]
    return "\n".join(lines) + "\n"


def main() -> int:
    art = ROOT / "artifacts"
    rows = load_dev6()
    off_cfg, on_cfg = off_config(), arm_config()
    off_c, on_c = score_rows(off_cfg, rows), score_rows(on_cfg, rows)
    off_r, on_r = _rob(off_cfg), _rob(on_cfg)
    sw = sweep(on_cfg)
    traps_off, traps_on = score_attribute_traps(off_cfg), score_attribute_traps(on_cfg)
    fresh = load_fresh()
    fx, ne = fixed_rows(off_c, on_c), new_errors(off_c, on_c)
    out = {
        "arm": ARM,
        "confirm": {
            "off": _pub(off_c), "on": _pub(on_c), "fixed": fx, "new_errors": ne,
            "must_refuse_rows": len(must_refuse_rows(rows)),
            "must_refuse_opened_off": opened_must_refuse(off_c, rows),
            "must_refuse_opened_on": opened_must_refuse(on_c, rows),
        },
        "robustness": {"off": off_r, "on": on_r,
                       "changed_vs_off": sorted(set(off_r["flips"].items()) ^ set(on_r["flips"].items()))},
        "sweep": {"n_queries": sw["n_queries"], "changed": sw["changed"], "n_opened": sw["n_opened"],
                  "labelled_trap_opened": [c["query"] for c in sw["labelled_trap_opened"]]},
        "traps": {k: {kk: v[kk] for kk in ("n", "n_opened", "opened")} for k, v in
                  (("off", traps_off), ("on", traps_on))},
        "fresh": {"off": fresh_score(off_cfg, fresh), "on": fresh_score(on_cfg, fresh)},
        "sign_test_p": sign_test_p(len(fx), len(ne)),
        "decision": confirm_decision(off_c, on_c, off_r, on_r, rows, sw, traps_on),
    }
    (art / "datamuse_dev6_confirm.json").write_text(json.dumps(out, indent=2, sort_keys=True) + "\n")
    md = _md(out, rows)
    (art / "datamuse_dev6_confirm.md").write_text(md, encoding="utf-8")
    print(md)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
