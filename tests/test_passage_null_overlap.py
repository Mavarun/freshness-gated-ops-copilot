"""Post-hoc overlap: the committed report and the cut logic agree."""

import json
from pathlib import Path

from ops_copilot.passage_null_exact import Node
from ops_copilot.passage_null_overlap import cut_profile

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
OV = json.loads((ROOT / "artifacts" / "passage_null_overlap.json").read_text())


def _call(pct, passed, vetoed, n=1000):
    below = np.zeros(n, dtype=bool)
    below[: int(round(pct * n))] = True
    return Node(word="w", below=below, passed=passed, vetoed=vetoed)


def test_cut_profile_on_toy_trees():
    leaf = lambda d: Node(decision=d)  # noqa: E731
    trees = {"trap": _call(0.30, leaf("ANSWER"), leaf("REFUSE_UNGROUNDED")),
             "keep": _call(0.50, leaf("ANSWER"), leaf("REFUSE_UNGROUNDED"))}
    rows = [{"id": "trap", "expect_decision": "REFUSE_UNGROUNDED"}, {"id": "keep", "expect_decision": "ANSWER"}]
    p = cut_profile(trees, rows, grid=(0.0, 0.2, 0.3, 0.4, 0.5, 0.6))
    assert p["open_up_to"] == {"trap": 0.3} and p["kept_up_to"] == {"keep": 0.5}
    assert p["free_and_safe_cuts"] == [0.4, 0.5]
    trees["keep"] = _call(0.25, leaf("ANSWER"), leaf("REFUSE_UNGROUNDED"))
    assert cut_profile(trees, rows, grid=(0.0, 0.2, 0.3, 0.4))["free_and_safe_cuts"] == []


def test_no_pool_cut_is_free_and_safe_on_the_spent_rows():
    p = OV["profile"]
    assert OV["n_rows"] == 247
    assert p["worst_trap_cut"] == 0.408 and max(p["open_up_to"], key=p["open_up_to"].get) == "at2-01"
    assert p["free_and_safe_cuts"] == []
    assert p["keep_rows_below_worst_trap"] == ["d2-17", "d3-02", "d3-09", "d3-10", "d3-23", "d5-02"]


def test_at2_01_is_credited_by_a_generic_word():
    assert OV["calls"]["at2-01"][0][:2] == ["taste", "one"]
    assert OV["calls"]["at-22"][1][:2] == ["flavour", "two"]
