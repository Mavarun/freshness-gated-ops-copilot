#!/usr/bin/env python3
"""Post-hoc probe: the passage-rescue word-meaning check -> artifacts/passage_sense_probe.{json,md}.

Why: the dev5 calibration found the shipped default answering the must-refuse
trap d5-38 (``What colour is the checkout_retry feature flag?``) through the
passage-support rescue ``colour <- default``. This compares the shipped
default with ``passage_support_sense_check=True`` on the dev5 calibration rows
(dev + dev2 + dev3 + dev4 + dev5 tune; never dev5 confirm or held-out), the
clean golden rows and the tests/ literal sweep. It selects nothing: the check
is opt-in and the shipped default is unchanged.
"""

from __future__ import annotations

import json
import sys
from dataclasses import replace
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ops_copilot.config import CopilotConfig  # noqa: E402
from ops_copilot.datamuse_dev5 import calibration_rows, opened_must_refuse  # noqa: E402
from ops_copilot.noun_gloss_sense_calibration import _clean_stats  # noqa: E402
from ops_copilot.safety_sweep import sweep  # noqa: E402
from ops_copilot.wordnet_dev2 import fixed_rows, new_errors, score_rows  # noqa: E402


def _pub(s: dict) -> dict:
    return {k: v for k, v in s.items() if k not in ("ok", "decisions")}


def main() -> int:
    rows = calibration_rows()
    off_cfg = CopilotConfig()
    on_cfg = replace(off_cfg, passage_support_sense_check=True)
    off, on = score_rows(off_cfg, rows), score_rows(on_cfg, rows)
    sw = sweep(on_cfg)
    errs = new_errors(off, on)
    by_set: dict[str, int] = {}
    for r in rows:
        if r["id"] in errs:
            by_set[r["set"]] = by_set.get(r["set"], 0) + 1
    rep = {
        "post_hoc": True,
        "n_rows": len(rows),
        "default": {**_pub(off), "clean": _clean_stats(off_cfg), "opened_must_refuse": opened_must_refuse(off, rows)},
        "sense_check": {**_pub(on), "clean": _clean_stats(on_cfg), "opened_must_refuse": opened_must_refuse(on, rows)},
        "fixed": fixed_rows(off, on),
        "new_errors": errs,
        "new_errors_by_set": dict(sorted(by_set.items())),
        "sweep_n_changed": len(sw["changed"]),
        "sweep_n_opened": sw["n_opened"],
        "sweep_labelled_trap_opened": [c["query"] for c in sw["labelled_trap_opened"]],
        "decision": "ships off: closes d5-38 but loses correct rows (no-new-error rule fails)",
    }
    art = ROOT / "artifacts"
    (art / "passage_sense_probe.json").write_text(json.dumps(rep, indent=2, sort_keys=True) + "\n")
    d, s = rep["default"], rep["sense_check"]
    lines = [
        "# Passage-rescue word-meaning check (post-hoc probe, selects nothing)",
        "",
        f"Rows: {len(rows)} dev5 calibration rows (no dev5 confirm, no held-out), 51 clean golden, tests/ sweep.",
        "",
        "| config | calib correct | calib ANSWER | fail-open | must-refuse opened | clean |",
        "| :--- | ---: | ---: | ---: | :--- | ---: |",
        f"| shipped default | {d['correct']}/{d['n']} | {d['answer_correct']}/{d['n_answer']} | {d['n_fail_open']} | "
        f"{', '.join(d['opened_must_refuse']) or '-'} | {d['clean']['clean_accuracy']:.3f} |",
        f"| + passage sense check | {s['correct']}/{s['n']} | {s['answer_correct']}/{s['n_answer']} | {s['n_fail_open']} | "
        f"{', '.join(s['opened_must_refuse']) or '-'} | {s['clean']['clean_accuracy']:.3f} |",
        "",
        f"Fixed: {', '.join(rep['fixed']) or '-'}. New errors: {len(errs)} "
        f"({', '.join(f'{k} {v}' for k, v in rep['new_errors_by_set'].items())}).",
        f"Sweep: {rep['sweep_n_changed']} changed decisions, {rep['sweep_n_opened']} opened, "
        f"{len(rep['sweep_labelled_trap_opened'])} labelled traps opened.",
        f"Decision: {rep['decision']}.",
        "",
    ]
    (art / "passage_sense_probe.md").write_text("\n".join(lines))
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
