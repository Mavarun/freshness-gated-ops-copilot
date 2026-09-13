#!/usr/bin/env python3
"""Full golden eval; writes artifacts/eval_report.md."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ops_copilot import Copilot  # noqa: E402
from ops_copilot.eval import render_markdown, run_eval  # noqa: E402


def main() -> None:
    artifacts = ROOT / "artifacts"
    artifacts.mkdir(parents=True, exist_ok=True)
    bot = Copilot()
    report = run_eval(
        bot,
        golden_path=ROOT / "data" / "golden" / "questions.jsonl",
        trace_path=artifacts / "traces.jsonl",
    )
    markdown = render_markdown(report)
    out = artifacts / "eval_report.md"
    out.write_text(markdown, encoding="utf-8")
    (artifacts / "eval_metrics.json").write_text(
        json.dumps(report.as_dict(), indent=2) + "\n", encoding="utf-8"
    )
    print(markdown)
    print(f"wrote {out}")
    print(f"wrote {artifacts / 'eval_metrics.json'}")
    print(f"wrote {artifacts / 'traces.jsonl'}")


if __name__ == "__main__":
    main()
