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

from dataclasses import replace  # noqa: E402

from ops_copilot.config import CopilotConfig  # noqa: E402
from ops_copilot.robustness import (  # noqa: E402
    EMBED_ABLATIONS,
    EMBEDDING_ON,
    PR10_BEFORE,
    leakage_report,
    load_before,
    render_robustness_markdown,
    run_ablations,
    run_robustness,
)

CALIBRATION = ROOT / "artifacts" / "semantic_grounding_calibration.json"


def _summary(rep) -> dict:
    d = rep.as_dict(flip_detail=False)
    keys = (
        "clean_accuracy",
        "clean_safety",
        "perturbed_accuracy",
        "n_flips",
        "n_fail_open",
        "fail_open",
        "n_spurious_write",
        "n_raw_pii_outputs",
        "flips",
    )
    return {k: d[k] for k in keys} | {
        "per_perturbation": {k: v["perturbed_accuracy"] for k, v in d["per_perturbation"].items()},
        "per_synonym_split": {
            k: {"perturbed_accuracy": v["perturbed_accuracy"], "n": v["n"], "by_gate": v["by_gate"]}
            for k, v in d["per_synonym_split"].items()
        },
        "per_gate": {k: v["perturbed_accuracy"] for k, v in d["per_gate"].items()},
    }


def _before_summary(before: dict) -> dict:
    keys = ("perturbed_accuracy", "n_flips", "n_fail_open", "n_spurious_write", "n_raw_pii_outputs")
    return {k: before[k] for k in keys} | {
        "per_perturbation": {k: v["perturbed_accuracy"] for k, v in before["per_perturbation"].items()},
        "per_synonym_split": {
            k: v["perturbed_accuracy"] for k, v in before["per_synonym_split"].items()
        },
        "per_gate": {k: v["perturbed_accuracy"] for k, v in before["per_gate"].items()},
    }


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
    ap.add_argument(
        "--before",
        default=None,
        help="frozen PR #11 per-row run (default: artifacts/robustness_pr11.json)",
    )
    args = ap.parse_args(argv)

    report = run_robustness(golden_path=args.golden, paraphrase_path=args.paraphrase)
    embedding = run_robustness(
        golden_path=args.golden,
        paraphrase_path=args.paraphrase,
        config=replace(CopilotConfig(), **EMBEDDING_ON),
    )
    before = load_before(args.before, paraphrase_path=args.paraphrase)
    before_pr10 = load_before(PR10_BEFORE, paraphrase_path=args.paraphrase)
    ablations = run_ablations(golden_path=args.golden, paraphrase_path=args.paraphrase)
    embed_ablations = run_ablations(
        golden_path=args.golden, paraphrase_path=args.paraphrase, grid=EMBED_ABLATIONS
    )
    leakage = leakage_report()
    calibration = (
        json.loads(CALIBRATION.read_text(encoding="utf-8"))["chosen"]
        if CALIBRATION.is_file()
        else None
    )
    out = Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    md_path = out / "robustness_report.md"
    json_path = out / "robustness_metrics.json"
    md_path.write_text(
        render_robustness_markdown(
            report,
            baseline=before,
            ablations=ablations,
            leakage=leakage,
            embedding=embedding,
            embed_ablations=embed_ablations,
            calibration=calibration,
        ),
        encoding="utf-8",
    )
    metrics = report.as_dict(flip_detail=False)
    if before:
        metrics["before_pr11"] = _before_summary(before)
    if before_pr10:
        metrics["before_pr10"] = _before_summary(before_pr10)
    metrics["embedding_on"] = _summary(embedding)
    metrics["embedding_ablations"] = embed_ablations
    if calibration:
        metrics["semantic_grounding_calibration"] = calibration
    metrics["ablations"] = ablations
    metrics["leakage"] = leakage
    metrics = _rounded(metrics)
    json_path.write_text(json.dumps(metrics, indent=1) + "\n", encoding="utf-8")

    print(
        f"clean_accuracy={report.clean_accuracy:.3f} (n={report.n_clean}) "
        f"perturbed_accuracy={report.perturbed_accuracy:.3f} (n={report.n_perturbed}) "
        f"flips={len(report.flips)} fail_open={len(report.fail_open)}"
        + (f" ({before['label']} {before['n_fail_open']})" if before else "")
    )
    for split, b in report.per_synonym_split.items():
        e = embedding.per_synonym_split.get(split, {})
        print(
            f"  synonym/{split:<8} acc={b['perturbed_accuracy']:.3f} n={b['n']} "
            f"(embedding on {e.get('perturbed_accuracy', 0.0):.3f})"
        )
    print(
        f"embedding on: clean={embedding.clean_accuracy:.3f} "
        f"perturbed={embedding.perturbed_accuracy:.3f} fail_open={len(embedding.fail_open)}"
    )
    for kind, b in report.per_perturbation.items():
        print(f"  {kind:<11} acc={b['perturbed_accuracy']:.3f} n={b['n']} flips={b['n_flips']}")
    print(f"wrote {md_path}")
    print(f"wrote {json_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
