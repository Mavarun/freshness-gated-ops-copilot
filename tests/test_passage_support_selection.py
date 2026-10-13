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


def test_committed_selection_is_consistent() -> None:
    out = json.loads(SEL.read_text())
    c = out["candidates"]
    assert out["baseline"] == "max_lex/r1/b1.5" and out["chosen"] in c and c[out["chosen"]]["kept"]
    assert _script().select(c) == out["chosen"]
    # the PR #19 recipe's hard negatives are much longer than real answers
    ln = out["length"]
    assert ln["max_lex"]["hard"]["median"] > 1.3 * ln["max_lex"]["own"]["median"]
    assert ln["length_matched"]["hard"]["median"] < 1.2 * ln["length_matched"]["own"]["median"]
    # chosen recipe ranks better on validation; cost on no-shared-word queries is recorded, not hidden
    assert c[out["chosen"]]["mrr"] > c[out["baseline"]]["mrr"]
    assert out["n_valid_questions"] < out["n_fit_questions"] / 5
