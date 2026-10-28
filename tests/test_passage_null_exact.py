"""Decision trees of the shipped null test reproduce every recorded seed and the pool mode."""

import json
from dataclasses import replace
from pathlib import Path

import numpy as np
import pytest

from ops_copilot.attribute_traps import load_traps
from ops_copilot.config import CopilotConfig
from ops_copilot.datamuse_dev5 import calibration_rows
from ops_copilot.passage_null_exact import (
    build_trees,
    depth,
    evaluate_sample,
    pool_decision,
    sample_distribution,
    seed_indices,
)
from ops_copilot.passage_support import control_words
from ops_copilot.pipeline import Copilot
from ops_copilot.synonym_dev4 import OPENING

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def built():
    rows, traps = calibration_rows(), load_traps()
    trees, pool = build_trees(rows + traps)
    return rows, traps, trees, pool


def test_seed_indices_are_the_shipped_sample(built):
    *_, pool = built
    g = Copilot(config=CopilotConfig()).grounder
    assert tuple(pool[i] for i in seed_indices(pool, 42)) == g.passage_null_controls
    assert len(set(seed_indices(pool, 7, 300))) == 300


@pytest.mark.parametrize("block,k", [("primary", 100), ("secondary_300_controls", 300)])
def test_trees_reproduce_every_recorded_seed_of_the_2026_10_26_sweep(built, block, k):
    rows, traps, trees, pool = built
    art = json.loads((ROOT / "artifacts" / "passage_null_seeds.json").read_text())[block]
    recs = {**art["seeds"], "42": art["reference"]}
    assert len(recs) == 21
    for seed, rec in recs.items():
        d = evaluate_sample(trees, seed_indices(pool, int(seed), k))
        assert sorted(t["id"] for t in traps if d[t["id"]] in OPENING) == rec["traps_opened"], seed
        assert sum(d[r["id"]] == r["expect_decision"] for r in rows) == rec["calib_correct"], seed


def test_trees_are_small_and_most_rows_never_reach_the_null_test(built):
    rows, traps, trees, _ = built
    live = [t for t in trees.values() if t.decision is None]
    assert 0 < len(live) < len(trees) / 2
    assert max(depth(t) for t in trees.values()) <= 6


def test_pool_decision_equals_a_real_pool_mode_run(built):
    _, traps, trees, _ = built
    for q in (0.30, 0.38):
        cfg = replace(CopilotConfig(), passage_support_null_pool=True, passage_support_null_min=q,
                      passage_support_credit_stop=False)  # the trees are of the 2026-10-27 default
        bot = Copilot(config=cfg)
        real = {t["id"]: bot.ask(t["query"]).decision.value for t in traps}
        assert real == {t["id"]: pool_decision(trees, q)[t["id"]] for t in traps}


def test_sample_distribution_is_reproducible_and_consistent(built):
    rows, traps, trees, pool = built
    a = sample_distribution(trees, rows, traps, len(pool), n_samples=200)
    b = sample_distribution(trees, rows, traps, len(pool), n_samples=200)
    assert a == b
    assert sum(a["traps_opened_hist"].values()) == 200
    assert 0.0 <= a["p_safe"] <= a["p_no_trap_open"] <= 1.0
    mean = sum(v * c for v, c in a["traps_opened_hist"].items()) / 200
    assert mean == pytest.approx(a["mean_traps_opened"])
    assert a["correct_p05_p95"][0] <= a["correct_mean"] <= a["correct_p05_p95"][1]


def test_control_words_sample_without_replacement_from_the_pool(built):
    *_, pool = built
    from ops_copilot.domain_vectors import default_vectors

    dv = default_vectors()
    w = control_words(dv, set(dv.index) - set(pool), k=100, seed=3)
    assert len(set(w)) == 100 and set(w) <= set(pool)
    assert np.all(np.diff(seed_indices(pool, 3)) != 0)
