"""The committed seed-free report agrees with the seed sweep it explains."""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXACT = json.loads((ROOT / "artifacts" / "passage_null_exact.json").read_text())
SEEDS = json.loads((ROOT / "artifacts" / "passage_null_seeds.json").read_text())


def test_seed_42_matches_the_recorded_reference():
    ref = SEEDS["primary"]["reference"]
    assert EXACT["seed_42"]["calib_correct"] == ref["calib_correct"] == 88
    assert EXACT["seed_42"]["traps_opened"] == ref["traps_opened"] == []
    assert EXACT["n_pool"] == 5067 and EXACT["n_rows"] == 171 and EXACT["n_traps"] == 36


def test_seed_42_was_a_lucky_draw():
    d = EXACT["sample_distribution"]["100"]
    assert d["n_samples"] == 10_000
    assert d["p_no_trap_open"] < 0.06  # the sweep saw 1 of 20 safe seeds
    assert d["p_open"]["at-22"] > 0.9 and 0.5 < d["p_open"]["at-12"] < 0.65
    # more controls make the estimate less noisy, not safer: at-22 sits above the cut
    assert EXACT["sample_distribution"]["300"]["p_no_trap_open"] < d["p_no_trap_open"]


def test_pool_grid_trades_traps_for_rows_monotonically():
    g = EXACT["pool_grid"]
    assert [x["q"] for x in g] == sorted(x["q"] for x in g)
    assert all(a["calib_correct"] >= b["calib_correct"] for a, b in zip(g, g[1:]))
    assert all(set(b["traps_opened"]) <= set(a["traps_opened"]) for a, b in zip(g, g[1:]))
    first_safe = next(x for x in g if not x["traps_opened"])
    assert first_safe["q"] == 0.38 and first_safe["calib_correct"] == 85
    assert all(not x["must_refuse_opened"] for x in g)
