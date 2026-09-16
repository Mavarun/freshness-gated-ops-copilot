#!/usr/bin/env python3
"""Full golden eval: SLA comparison + BM25-only vs dual disagreement; writes artifacts/."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ops_copilot.eval import (  # noqa: E402
    render_comparison_markdown,
    render_markdown,
    run_comparison,
)
from ops_copilot.disagreement_compare import (  # noqa: E402
    render_disagreement_comparison_markdown,
    run_disagreement_comparison,
)


def main() -> None:
    artifacts = ROOT / "artifacts"
    artifacts.mkdir(parents=True, exist_ok=True)
    golden = ROOT / "data" / "golden" / "questions.jsonl"
    corpus = ROOT / "data" / "corpus" / "ops_docs.jsonl"

    comparison = run_comparison(
        golden_path=golden,
        corpus_path=corpus,
        trace_path=artifacts / "traces.jsonl",
    )

    per_md = render_markdown(comparison.per_source_report)
    (artifacts / "eval_report.md").write_text(per_md, encoding="utf-8")
    (artifacts / "eval_metrics.json").write_text(
        json.dumps(comparison.per_source_report.as_dict(), indent=2) + chr(10),
        encoding="utf-8",
    )

    cmp_md = render_comparison_markdown(comparison)
    (artifacts / "eval_comparison.md").write_text(cmp_md, encoding="utf-8")
    (artifacts / "eval_comparison.json").write_text(
        json.dumps(comparison.as_dict(), indent=2) + chr(10),
        encoding="utf-8",
    )

    disagree = run_disagreement_comparison(
        golden_path=golden,
        corpus_path=corpus,
    )
    d_md = render_disagreement_comparison_markdown(disagree)
    (artifacts / "eval_disagreement.md").write_text(d_md, encoding="utf-8")
    (artifacts / "eval_disagreement.json").write_text(
        json.dumps(disagree.as_dict(), indent=2) + chr(10),
        encoding="utf-8",
    )

    print(cmp_md)
    print(d_md)
    print(f"wrote {artifacts / 'eval_report.md'}")
    print(f"wrote {artifacts / 'eval_metrics.json'}")
    print(f"wrote {artifacts / 'eval_comparison.md'}")
    print(f"wrote {artifacts / 'eval_comparison.json'}")
    print(f"wrote {artifacts / 'eval_disagreement.md'}")
    print(f"wrote {artifacts / 'eval_disagreement.json'}")
    print(f"wrote {artifacts / 'traces.jsonl'}")


if __name__ == "__main__":
    main()
