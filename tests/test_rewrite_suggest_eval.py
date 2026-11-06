from ops_copilot.rewrite_suggest import SuggestConfig
from ops_copilot.rewrite_suggest_eval import (
    CALIBRATION_FILES,
    EvalRow,
    _anchors_from_swap,
    load_heldout_rows,
    load_rows,
    score_arm,
)


def test_anchor_parsing_handles_multi_swaps():
    assert _anchors_from_swap("latency -> sluggishness") == ("latency",)
    assert _anchors_from_swap("current -> present, latency -> lag") == ("current", "latency")
    assert _anchors_from_swap("") == ()


def test_heldout_rows_are_the_nine_answer_rows_plus_writes():
    rows = load_heldout_rows()
    answer = [r for r in rows if r.expect == "ANSWER"]
    assert len(answer) == 9
    g00 = next(r for r in rows if r.id == "g00-synonym")
    assert "latency" in g00.anchors


def test_calibration_files_load():
    rows = load_rows(CALIBRATION_FILES)
    assert len(rows) == 43 + 45 + 44 + 44 + 45
    traps = [r for r in rows if r.source_index < 0]
    assert traps and all(r.expect.startswith("REFUSE_") for r in traps)


def test_score_arm_counts_rescuable_traps_and_null():
    rows = [
        EvalRow("x1", "What is the left error allowance for checkout?", 4, "ANSWER", ("remaining", "budget"), "t"),
        EvalRow("x2", "What is the current checkout p99 latency?", 0, "ANSWER", ("latency",), "t"),
    ]
    sc = score_arm(rows, SuggestConfig(rank="context"), null_draws=3)
    assert sc.n_rescuable == 1  # x2 is answered by the default, so it is not rescuable
    assert sc.anchor_hit_3 == 1 and sc.anchor_hit_1 == 1
    assert sc.rates()["anchor_precision_1"] == 1.0
    assert sc.null_tried == 3
    r = sc.rates()
    assert 0 <= r["null_verify_rate"] <= 1 and r["coverage"] == 1.0


def test_strict_anchor_needs_the_typed_slot():
    rows = load_heldout_rows()
    g00 = next(r for r in rows if r.id == "g00-synonym")
    assert "lag" in g00.swapped and "present" in g00.swapped
    sc = score_arm([g00], SuggestConfig(rank="context", min_context=2))
    # the confirm's only g00 hit swaps 'present' for 'latency': loose hit, not strict
    assert sc.anchor_hit_3 == 1
    assert sc.strict_anchor_hit_3 == 0


def test_swap_right_side_is_parsed():
    assert _anchors_from_swap("latency -> sluggishness", 1) == ("sluggishness",)
