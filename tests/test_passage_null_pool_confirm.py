"""The one-shot seed-free confirm is recorded and its decision follows the registered rule."""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONF = json.loads((ROOT / "artifacts" / "passage_null_pool_confirm.json").read_text())


def test_the_chosen_arm_is_the_calibration_choice():
    cal = json.loads((ROOT / "artifacts" / "passage_null_pool_calibration.json").read_text())
    assert CONF["chosen"] == {k: cal["chosen"][k] for k in ("null_min", "pool", "sticky")}
    assert CONF["chosen"]["null_min"] == 0.4


def test_a_fresh_trap_opens_in_both_configs_so_the_arm_ships_off():
    t = CONF["traps_v2_confirm"]
    assert t["shipped"]["opened"] == t["pool"]["opened"] == ["at2-01"]
    checks = CONF["decision"]["checks"]
    assert [k for k, v in checks.items() if not v] == ["traps_v2_confirm_none_open"]
    assert CONF["decision"]["default_on"] is False


def test_shipped_default_would_open_a_v2_confirm_trap_under_almost_any_sample():
    so = CONF["traps_v2_confirm"]["shipped_over_samples"]
    assert so["n_samples"] == 10_000 and so["p_at_least_one_open"] > 0.98


def test_the_arm_costs_nothing_on_the_203_rows_and_one_dev6_row():
    r = CONF["robustness"]
    assert r["changed"] == []
    assert r["pool"]["perturbed_accuracy"] == r["shipped"]["perturbed_accuracy"]
    d6 = CONF["dev6_spent_recorded_only"]
    assert (d6["shipped"]["correct"], d6["pool"]["correct"]) == (21, 20) and d6["new_errors"] == ["d6-20"]
