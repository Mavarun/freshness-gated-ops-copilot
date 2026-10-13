"""Training-recipe selection for the passage classifier (validation questions only)."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SEL = ROOT / "artifacts" / "passage_support_selection.json"


def _script():
    spec = importlib.util.spec_from_file_location("select_ps", ROOT / "scripts" / "select_passage_support.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _row(lm: float, mrr: float, r: int = 1, b: float = 1.5) -> dict:
    return {"vs_hard_len": lm, "mrr": mrr, "n_random": r, "band": b}


def test_rule_drops_candidates_that_lose_length_matched_auc() -> None:
    sel = _script().select
    rows = {"base": _row(0.80, 0.70), "better_mrr_worse_auc": _row(0.79, 0.90), "ok": _row(0.797, 0.75)}
    assert sel(rows, baseline="base", tol=0.005) == "ok"
    assert sel(rows, baseline="base", tol=0.02) == "better_mrr_worse_auc"


def test_rule_breaks_ties_towards_fewer_random_negatives_then_narrow_band() -> None:
    sel = _script().select
    rows = {"base": _row(0.80, 0.70), "a": _row(0.80, 0.75, r=3), "b": _row(0.80, 0.75, r=2, b=2.0), "c": _row(0.80, 0.75, r=2, b=1.25)}
    assert sel(rows, baseline="base") == "c"
