"""Calibrate the semantic grounding threshold on clean golden + dev rows only.

The calibration set is the 51 clean golden queries plus the perturbed
synonym rows tagged ``dev`` by ``data/golden/synonym_split.json``. Held-out
synonym rows (and the typo / word-order / polite rows) are never scored here,
and ``calibration_rows`` raises if a held-out row ever slips in.

Grid: every ``semantic_grounding_threshold`` in ``GRID`` for each
``semantic_grounding_max_terms`` in ``MAX_TERMS``, with the frozen embedding
fixture (both the dense retriever and the grounding backoff on). Selection:

1. feasible: clean accuracy 1.000, and zero fail-open, zero spurious
   PROPOSE_WRITE and zero raw PII outputs on the calibration rows;
2. highest calibration decision accuracy;
3. smallest ``max_terms`` (fewer rescued words is safer);
4. the midpoint of the widest contiguous run of optimal thresholds
   (max-margin choice between the nearest wrong rescue and the nearest gain).
"""

from __future__ import annotations

from dataclasses import replace

import numpy as np

from ops_copilot.config import CopilotConfig
from ops_copilot.cost_budget import SessionCostLedger
from ops_copilot.eval import load_golden
from ops_copilot.paraphrase_set import load_paraphrase_set
from ops_copilot.pii import detect_pii
from ops_copilot.pipeline import Copilot
from ops_copilot.synonym_split import DEFAULT_SPLIT_PATH, row_splits

GRID: tuple[float, ...] = tuple(round(float(x), 3) for x in np.arange(0.30, 0.9501, 0.005))
MAX_TERMS: tuple[int, ...] = (1, 2)
WRITE = "PROPOSE_WRITE"


def calibration_rows() -> list[tuple[str, str, dict]]:
    """(row_id, group, row) for clean golden + dev synonym rows; never held-out."""
    splits = row_splits(DEFAULT_SPLIT_PATH)
    out: list[tuple[str, str, dict]] = [
        (f"clean-g{i:02d}", "clean", dict(g)) for i, g in enumerate(load_golden())
    ]
    for row in load_paraphrase_set():
        rid = str(row["id"])
        if row["perturbation"] == "synonym" and splits.get(rid) == "dev":
            out.append((rid, "dev", dict(row)))
    leaked = [rid for rid, _, _ in out if splits.get(rid) == "heldout"]
    if leaked:
        raise AssertionError(f"held-out rows in calibration set: {leaked}")
    return out


def score(bot: Copilot, rows: list[tuple[str, str, dict]]) -> dict:
    bot.ledger = SessionCostLedger()
    wrong: list[str] = []
    fail_open: list[str] = []
    spurious: list[str] = []
    raw_pii = 0
    clean_ok = clean_n = 0
    for rid, group, row in rows:
        sid = row.get("session_id")
        if sid and "seed_session_spent" in row:
            bot.ledger.seed(str(sid), float(row["seed_session_spent"]))
        res = bot.ask(str(row["query"]), session_id=str(sid) if sid else None)
        got, want = res.decision.value, str(row["expect_decision"])
        raw_pii += bool(detect_pii(res.answer or ""))
        if group == "clean":
            clean_n += 1
            clean_ok += got == want
        if got != want:
            wrong.append(f"{rid}:{want}->{got}")
            if got == "ANSWER":
                fail_open.append(rid)
            if got == WRITE:
                spurious.append(rid)
    n = len(rows)
    return {
        "accuracy": (n - len(wrong)) / n if n else 0.0,
        "clean_accuracy": clean_ok / clean_n if clean_n else 0.0,
        "n_fail_open": len(fail_open),
        "n_spurious_write": len(spurious),
        "n_raw_pii_outputs": raw_pii,
        "wrong": wrong,
    }


def _feasible(r: dict) -> bool:
    return (
        r["clean_accuracy"] == 1.0
        and r["n_fail_open"] == 0
        and r["n_spurious_write"] == 0
        and r["n_raw_pii_outputs"] == 0
    )


def select(results: list[dict]) -> dict:
    """Apply the selection rule in the module docstring to grid results."""
    feasible = [r for r in results if _feasible(r)]
    if not feasible:
        raise RuntimeError("no feasible semantic grounding threshold")
    best_acc = max(r["accuracy"] for r in feasible)
    tops = [r for r in feasible if r["accuracy"] == best_acc]
    mt = min(r["max_terms"] for r in tops)
    ok = {r["threshold"] for r in tops if r["max_terms"] == mt}
    runs: list[list[float]] = []
    for th in GRID:
        if th in ok:
            if runs and runs[-1][-1] == GRID[GRID.index(th) - 1]:
                runs[-1].append(th)
            else:
                runs.append([th])
    widest = max(runs, key=len)
    mid = widest[(len(widest) - 1) // 2]
    return {
        "threshold": float(mid),
        "max_terms": int(mt),
        "accuracy": float(best_acc),
        "optimal_run": [float(widest[0]), float(widest[-1])],
    }


def calibrate(base: CopilotConfig | None = None) -> dict:
    base = base or CopilotConfig()
    rows = calibration_rows()
    results: list[dict] = []
    for mt in MAX_TERMS:
        cfg = replace(
            base,
            embedding_backend="frozen",
            embed_dense_retriever=True,
            embed_semantic_grounding=True,
            semantic_grounding_max_terms=mt,
        )
        bot = Copilot(config=cfg)
        es = bot.grounder.embed_support
        assert es is not None
        for th in GRID:
            es.threshold = th
            results.append({"threshold": th, "max_terms": mt} | score(bot, rows))
    chosen = select(results)
    return {
        "calibration_rows": [rid for rid, _, _ in rows],
        "n_clean": sum(1 for _, g, _ in rows if g == "clean"),
        "n_dev": sum(1 for _, g, _ in rows if g == "dev"),
        "grid": list(GRID),
        "max_terms": list(MAX_TERMS),
        "chosen": chosen,
        "results": results,
    }
