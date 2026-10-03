"""Run the hand-written write-intent eval and write its artifacts.

    python scripts/run_write_intent_eval.py            # deterministic json + md
    python scripts/run_write_intent_eval.py --latency  # also time the classifier

``artifacts/write_intent_eval.{json,md}`` (the original 48 rows) and
``artifacts/write_intent_eval_phrasal.{json,md}`` (the 39 phrasal rows,
reported separately) are deterministic (frozen embedding fixture, no
timings) and are checked by the test suite. The phrasal "before" column is
``artifacts/write_intent_eval_phrasal_pr13.json``, a frozen run of the PR #13
write gate (git worktree at 135c57f) on the same rows.
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
    load_phrasal_eval,
    load_write_eval,
    pr12_keyword_detector,
    run_phrasal_grid,
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


def render_phrasal_md(grid: dict[str, dict], pr13: dict | None) -> str:
    rows = load_phrasal_eval()
    any_run = next(iter(grid.values()))
    full = {}
    if pr13:
        full["PR #13 write gate (frozen run), default"] = pr13["configs"]["+ mood detection (default)"]
    full.update(grid)
    lines = [
        "# Write-intent eval, phrasal rows (hand-written, reported separately)",
        "",
        f"{any_run['n']} new rows written by hand after the phrasal parser, by its author: "
        f"{any_run['n_write']} writes (particle verbs, cache-tool verbs, role pages), "
        f"{any_run['n_ambiguous']} ambiguous (unregistered / misspelled targets, page without a "
        f"recipient, conditional, two targets, a service given a value) and {any_run['n_read']} reads. "
        "No held-out word appears, so the held-out phrasal verbs themselves (set, turn, down, flush, "
        "purge) are not in this set; the unit tests cover them. Regression check, not a benchmark.",
        "",
        "| config | precision | recall | exact action+target | spurious writes | clarification recall | over-asking | reason code | did-you-mean |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for label, r in full.items():
        code = (
            f"{r['n_reason_code_correct']}/{r['n_reason_code_expected']}" if "n_reason_code_expected" in r else "n/a"
        )
        sugg = f"{r['n_suggestion_correct']}/{r['n_suggestion_expected']}" if "n_suggestion_expected" in r else "n/a"
        lines.append(
            f"| {label} | {r['precision']:.3f} | {r['recall']:.3f} ({r['tp']}/{r['n_write']}) | "
            f"{r['exact_action_target']}/{r['n_write']} | {r['n_spurious_write']} | "
            f"{r['clarification_recall']:.3f} | {r['n_over_asking']} | {code} | {sugg} |"
        )
    lines += ["", "## Per row", ""]
    labels = list(full)
    lines.append("| id | label | query | " + " | ".join(labels) + " |")
    lines.append("|---|---|---|" + "---|" * len(labels))
    short = {"PROPOSE_WRITE": "WRITE", "REFUSE_AMBIGUOUS_WRITE": "ASK"}
    for i, row in enumerate(rows):
        cells = []
        for label in labels:
            pr = full[label]["rows"][i]
            d = short.get(pr["decision"], pr["decision"].replace("REFUSE_", "R_"))
            if pr["decision"] == "PROPOSE_WRITE":
                d += f" {pr['action']}:{pr['target']}"
            elif pr.get("reason_code"):
                d += f" {pr['reason_code']}"
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
    from ops_copilot.robustness import run_robustness

    lines += [
        "",
        "Full pipeline over the 203 perturbed robustness rows (ms per query, "
        "`RobustnessReport.latency_summary`):",
        "",
        "| config | p50 ms | p95 ms | mean ms |",
        "|---|---|---|---|",
    ]
    for label, knobs in WRITE_EVAL_CONFIGS.items():
        lat = run_robustness(config=replace(CopilotConfig(), **knobs)).latency_summary()
        lines.append(f"| {label} | {lat['p50']:.2f} | {lat['p95']:.2f} | {lat['mean']:.2f} |")
    return "\n".join(lines) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--latency", action="store_true")
    args = ap.parse_args()
    grid = run_write_eval_grid()
    ART.mkdir(exist_ok=True)
    (ART / "write_intent_eval.json").write_text(json.dumps(grid, indent=2, sort_keys=True) + "\n")
    (ART / "write_intent_eval.md").write_text(render_md(grid))
    phrasal = run_phrasal_grid()
    pr13_path = ART / "write_intent_eval_phrasal_pr13.json"
    pr13 = json.loads(pr13_path.read_text()) if pr13_path.is_file() else None
    (ART / "write_intent_eval_phrasal.json").write_text(json.dumps(phrasal, indent=2, sort_keys=True) + "\n")
    (ART / "write_intent_eval_phrasal.md").write_text(render_phrasal_md(phrasal, pr13))
    for name, g in (("original 48", grid), ("phrasal 39", phrasal)):
        print(f"-- {name}")
        for label, r in g.items():
            print(
                f"{label:50s} P={r['precision']:.3f} R={r['recall']:.3f} "
                f"spurious={r['n_spurious_write']} clar={r['clarification_recall']:.3f}"
            )
    if args.latency:
        md = latency_md()
        (ART / "write_intent_latency.md").write_text(md)
        print(md)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
