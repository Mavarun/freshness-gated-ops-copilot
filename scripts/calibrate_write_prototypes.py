#!/usr/bin/env python3
"""Calibrate the write-prototype backoff (threshold, margin) on dev verbs only.

Data: ``data/write/prototype_dev.jsonl``, a hand-written list of verbs that
are in no write lexicon and in no held-out word list, each with the target
kind it is aimed at and the action it should map to (or ``none`` for reads,
unsupported mutations and nonsense). Prototypes come from the lexicons
(``write_prototypes.prototype_texts``). The held-out synonym rows, the clean
golden set and the hand-written write-intent eval set are not used.

Grid: threshold 0.50..0.95 and margin 0.00..0.20 in steps of 0.01. A config
is feasible when it accepts no ``none`` verb and maps no positive to the
wrong action, *and* stays so with both knobs loosened by ``BUFFER`` (0.02),
so no dev negative sits within 0.02 of being accepted. Among feasible
configs with the most correct positives the most conservative one wins
(largest margin, then largest threshold): a stricter setting can only cost
recall, never safety.

Vectors: the live model when it is cached, else the frozen fixture
(``data/embeddings/minilm_write.npz``). Writes
``artifacts/write_prototype_calibration.{json,md}``.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ops_copilot.embeddings import resolve_backend  # noqa: E402
from ops_copilot.write_prototypes import (  # noqa: E402
    CALIBRATION,
    class_scores,
    decide,
    load_dev_set,
    prototype_texts,
    span,
)

THRESHOLDS = [round(0.50 + 0.01 * i, 2) for i in range(46)]
MARGINS = [round(0.01 * i, 2) for i in range(21)]
BUFFER = 0.02


def evaluate(scored: list[tuple[dict, dict]], threshold: float, margin: float) -> dict:
    tp = wrong = fp = 0
    for row, scores in scored:
        res = decide(scores, row["kind"], threshold, margin)
        if not res["accepted"]:
            continue
        if row["label"] == "none":
            fp += 1
        elif res["action"] == row["label"]:
            tp += 1
        else:
            wrong += 1
    n_pos = sum(1 for r, _ in scored if r["label"] != "none")
    return {
        "threshold": threshold,
        "margin": margin,
        "correct": tp,
        "wrong_action": wrong,
        "false_accept": fp,
        "n_positive": n_pos,
        "n_negative": len(scored) - n_pos,
        "feasible": wrong == 0 and fp == 0,
    }


def select(grid: list[dict]) -> dict:
    feasible = [g for g in grid if g["feasible"] and g.get("buffer_ok", True)]
    best = max(g["correct"] for g in feasible)
    top = [g for g in feasible if g["correct"] == best]
    margin = max(g["margin"] for g in top)
    run = sorted(g["threshold"] for g in top if g["margin"] == margin)
    chosen = next(g for g in top if g["margin"] == margin and g["threshold"] == run[-1])
    return chosen | {"optimal_threshold_run": [run[0], run[-1]]}


def main() -> int:
    backend = resolve_backend("auto")
    protos = {c: np.vstack(backend.lookup(list(t))) for c, t in prototype_texts().items()}
    rows = load_dev_set()
    scored = []
    for row in rows:
        vec = backend.vector(span(row["verb"], row["kind"]))
        if vec is None:
            raise SystemExit(f"no vector for dev span {span(row['verb'], row['kind'])!r}")
        scored.append((row, class_scores(vec, protos)))
    grid = [evaluate(scored, t, m) for t in THRESHOLDS for m in MARGINS]
    for g in grid:
        loose = evaluate(scored, round(g["threshold"] - BUFFER, 2), round(max(g["margin"] - BUFFER, 0.0), 2))
        g["buffer_ok"] = loose["feasible"]
    chosen = select(grid)
    per_row = []
    for row, scores in scored:
        res = decide(scores, row["kind"], chosen["threshold"], chosen["margin"])
        per_row.append(
            {
                "verb": row["verb"],
                "kind": row["kind"],
                "label": row["label"],
                "nearest": res["action"],
                "cosine": res["cosine"],
                "margin": res["margin"],
                "accepted": res["accepted"],
            }
        )
    out = {
        "backend": backend.name,
        "n_dev": len(rows),
        "chosen": {k: chosen[k] for k in ("threshold", "margin", "correct", "n_positive", "optimal_threshold_run")},
        "per_row": per_row,
    }
    CALIBRATION.write_text(json.dumps(out, indent=1) + "\n", encoding="utf-8")
    lines = [
        "# Write-prototype backoff calibration (dev verbs only)",
        "",
        f"{len(rows)} hand-written dev verbs ({chosen['n_positive']} with an action, "
        f"{len(rows) - chosen['n_positive']} reads / unsupported / nonsense), none in a "
        "write lexicon or the held-out list. Backend: "
        f"`{backend.name}`.",
        "",
        f"Chosen: threshold **{chosen['threshold']}**, margin **{chosen['margin']}** "
        f"(feasible with a {BUFFER} buffer; optimal threshold run "
        f"{chosen['optimal_threshold_run']}, the strictest end taken); "
        f"{chosen['correct']} of {chosen['n_positive']} dev positives accepted with the right "
        "action, 0 negatives accepted, 0 wrong actions.",
        "",
        "| verb | kind | label | nearest | cosine | margin | accepted |",
        "| --- | --- | --- | --- | ---: | ---: | --- |",
    ]
    for r in per_row:
        lines.append(
            f"| {r['verb']} | {r['kind']} | {r['label']} | {r['nearest']} | "
            f"{r['cosine']:.3f} | {r['margin']:.3f} | {'yes' if r['accepted'] else 'no'} |"
        )
    CALIBRATION.with_suffix(".md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines[:6]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
