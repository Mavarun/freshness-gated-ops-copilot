"""Run the hand-written write-intent eval and write its artifacts.

    python scripts/run_write_intent_eval.py            # deterministic json + md
    python scripts/run_write_intent_eval.py --latency  # also time the classifier

``artifacts/write_intent_eval.{json,md}`` are deterministic (frozen
embedding fixture, no timings) and are checked by the test suite.
Latency is machine-dependent and goes to ``artifacts/write_intent_latency.md``.
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
import time
from dataclasses import replace
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ops_copilot.config import CopilotConfig  # noqa: E402
from ops_copilot.write_eval import (  # noqa: E402
    WRITE_EVAL_CONFIGS,
    load_write_eval,
    pr12_keyword_detector,
    run_write_eval_grid,
)

ART = ROOT / "artifacts"


def render_md(grid: dict[str, dict]) -> str:
    rows = load_write_eval()
    any_run = next(iter(grid.values()))
    lines = [
        "# Write-intent eval (hand-written)",
        "",
        f"{any_run['n']} phrasings written by hand for this slice: {any_run['n_write']} writes, "
        f"{any_run['n_read']} non-writes (informational + adversarial), {any_run['n_ambiguous']} "
        "ambiguous instructions. Only non-held-out vocabulary (enforced by a test). Written by "
        "the parser's author after the parser existed, so this is a regression check on fresh "
        "phrasings, not an unbiased benchmark.",
        "",
        "| config | precision | recall | exact action+target | spurious writes (rate) | clarification recall | over-asking |",
        "|---|---|---|---|---|---|---|",
    ]
    for label, r in grid.items():
        lines.append(
            f"| {label} | {r['precision']:.3f} | {r['recall']:.3f} ({r['tp']}/{r['n_write']}) | "
            f"{r['exact_action_target']}/{r['n_write']} | {r['n_spurious_write']} "
            f"({r['spurious_write_rate']:.3f}) | {r['clarification_recall']:.3f} | {r['n_over_asking']} |"
        )
    lines += ["", "## Per row (decision per config)", ""]
    labels = list(grid)
    lines.append("| id | label | query | " + " | ".join(labels) + " |")
    lines.append("|---|---|---|" + "---|" * len(labels))
    short = {"PROPOSE_WRITE": "WRITE", "REFUSE_AMBIGUOUS_WRITE": "ASK"}
    for i, row in enumerate(rows):
        cells = []
        for label in labels:
            pr = grid[label]["rows"][i]
            d = short.get(pr["decision"], pr["decision"].replace("REFUSE_", "R_"))
            if pr["decision"] == "PROPOSE_WRITE":
                d += f" {pr['action']}:{pr['target']}"
            cells.append(d)
        q = row["query"].replace("|", "\\|")
        lines.append(f"| {row['id']} | {row['label']} | {q} | " + " | ".join(cells) + " |")
    return "\n".join(lines) + "\n"


def _time(fn, queries, reps: int) -> tuple[float, float]:
    samples = []
    for _ in range(reps):
        for q in queries:
            t0 = time.perf_counter()
            fn(q)
            samples.append((time.perf_counter() - t0) * 1e6)
    samples.sort()
    return statistics.median(samples), samples[int(0.95 * (len(samples) - 1))]


def latency_md(reps: int = 20) -> str:
    from ops_copilot.pipeline import Copilot
    from ops_copilot.write_intent import classify_write_intent
    from ops_copilot.write_prototypes import PrototypeMatcher  # noqa: F401

    queries = [r["query"] for r in load_write_eval()]
    lines = [
        "# Write-intent latency",
        "",
        f"Machine-dependent; {len(queries)} eval queries x {reps} reps, single thread, "
        "frozen embedding fixture (no model load). Microseconds.",
        "",
        "| component | p50 us | p95 us |",
        "|---|---|---|",
    ]
    p50, p95 = _time(pr12_keyword_detector, queries, reps)
    lines.append(f"| PR #12 keyword regex | {p50:.0f} | {p95:.0f} |")
    for label, knobs in WRITE_EVAL_CONFIGS.items():
        bot = Copilot(config=replace(CopilotConfig(), **knobs))
        kw = dict(
            registry=bot.registry,
            typo_tolerance=bot.config.typo_tolerance,
            mood_detection=bot.config.write_mood_detection,
            prototypes=bot.write_prototypes,
            min_confidence=bot.config.write_min_confidence,
        )
        p50, p95 = _time(lambda q: classify_write_intent(q, **kw), queries, reps)
        lines.append(f"| classifier: {label} | {p50:.0f} | {p95:.0f} |")
    for label, knobs in WRITE_EVAL_CONFIGS.items():
        bot = Copilot(config=replace(CopilotConfig(), **knobs))
        p50, p95 = _time(bot.ask, queries, max(1, reps // 4))
        lines.append(f"| full pipeline ask: {label} | {p50:.0f} | {p95:.0f} |")
    return "\n".join(lines) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--latency", action="store_true")
    args = ap.parse_args()
    grid = run_write_eval_grid()
    ART.mkdir(exist_ok=True)
    (ART / "write_intent_eval.json").write_text(json.dumps(grid, indent=2, sort_keys=True) + "\n")
    (ART / "write_intent_eval.md").write_text(render_md(grid))
    for label, r in grid.items():
        print(
            f"{label:45s} P={r['precision']:.3f} R={r['recall']:.3f} "
            f"spurious={r['n_spurious_write']} clar={r['clarification_recall']:.3f}"
        )
    if args.latency:
        md = latency_md()
        (ART / "write_intent_latency.md").write_text(md)
        print(md)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
