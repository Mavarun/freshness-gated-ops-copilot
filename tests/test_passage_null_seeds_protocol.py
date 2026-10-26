"""Pre-registered seed-sensitivity protocol for the shipped null-control test (no seed sweep runs here)."""

from ops_copilot.config import CopilotConfig
from ops_copilot.passage_null_seeds import (
    CALIB_TOLERANCE,
    REFERENCE_SEED,
    SEEDS,
    is_safe,
    is_stable,
    seed_config,
)


def test_seeds_and_reference_are_fixed():
    assert SEEDS == tuple(range(1, 21)) and REFERENCE_SEED not in SEEDS and CALIB_TOLERANCE == 3


def test_seed_config_changes_only_the_seed_and_control_count():
    base, cfg = CopilotConfig(), seed_config(7, 300)
    assert (cfg.passage_support_null_seed, cfg.passage_support_null_controls) == (7, 300)
    same = {k: v for k, v in vars(cfg).items() if k not in ("passage_support_null_seed", "passage_support_null_controls")}
    assert same == {k: v for k, v in vars(base).items() if k in same}
    assert seed_config(REFERENCE_SEED) == base


def _r(calib=88, traps=(), opened=(), clean=1.0):
    return {"clean_accuracy": clean, "calib_correct": calib, "traps_opened": list(traps),
            "must_refuse_opened": list(opened)}


def test_stability_rule():
    ref = _r()
    assert is_stable({1: _r(86), 2: _r(91)}, ref)["stable"]
    v = is_stable({1: _r(84), 2: _r(traps=["at-03"]), 3: _r(opened=["d5-38"]), 4: _r(clean=0.98)}, ref)
    assert v == {"unsafe_seeds": [2, 3, 4], "drift_seeds": [1], "stable": False}
    assert is_safe(_r()) and not is_safe(_r(traps=["x"]))
