#!/usr/bin/env python3
"""Clean vs perturbed robustness eval -> artifacts/robustness_report.md + JSON.

Exit code is 0 regardless of accuracy: the drop is the finding, not a CI gate.
Any exception (bad data, pipeline crash) propagates and fails the job.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ops_copilot.robustness import (  # noqa: E402
    render_robustness_markdown,
    run_robustness,
)


def _rounded(obj):
    if isinstance(obj, float):
        return round(obj, 4)
    if isinstance(obj, dict):
        return {k: _rounded(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_rounded(v) for v in obj]
    return obj


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--golden", default=None, help="clean golden jsonl (default: data/golden)")
    ap.add_argument("--paraphrase", default=None, help="perturbed jsonl (default: data/golden)")
    ap.add_argument("--out-dir", default=str(ROOT / "artifacts"))
    args = ap.parse_args(argv)

    report = run_robustness(golden_path=args.golden, paraphrase_path=args.paraphrase)
    out = Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    md_path = out / "robustness_report.md"
    json_path = out / "robustness_metrics.json"
    md_path.write_text(render_robustness_markdown(report), encoding="utf-8")
    metrics = _rounded(report.as_dict(flip_detail=False))
    json_path.write_text(json.dumps(metrics, indent=1) + "\n", encoding="utf-8")

    print(
        f"clean_accuracy={report.clean_accuracy:.3f} (n={report.n_clean}) "
        f"perturbed_accuracy={report.perturbed_accuracy:.3f} (n={report.n_perturbed}) "
        f"flips={len(report.flips)}"
    )
    for kind, b in report.per_perturbation.items():
        print(f"  {kind:<11} acc={b['perturbed_accuracy']:.3f} n={b['n']} flips={b['n_flips']}")
    print(f"wrote {md_path}")
    print(f"wrote {json_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
