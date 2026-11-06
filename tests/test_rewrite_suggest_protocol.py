from ops_copilot.rewrite_suggest_protocol import (
    ARMS,
    MAX_TRAP_INVITATION,
    MIN_HELDOUT_ANCHOR_3,
    MIN_PRECISION,
    pick,
    ships,
)


def _r(a1, prec, trap):
    return {"anchor_hit_1": a1, "anchor_precision_1": prec, "trap_invitation": trap}


def test_protocol_constants_are_frozen():
    assert list(ARMS) == ["idf", "first", "context", "context_mc1", "context_mc2", "context_pairs",
                          "context_mc1_pairs"]
    assert (MAX_TRAP_INVITATION, MIN_PRECISION, MIN_HELDOUT_ANCHOR_3) == (0.40, 0.50, 3)


def test_pick_respects_budgets_and_ties_go_to_earlier_arm():
    cal = {"idf": _r(0.9, 0.9, 0.5), "first": _r(0.4, 0.6, 0.1), "context": _r(0.4, 0.7, 0.2)}
    assert pick(cal) == "first"
    assert pick({"idf": _r(0.9, 0.4, 0.1)}) is None


def test_ship_rule_needs_heldout_and_confirm():
    assert ships(_r(0.5, 0.6, 0.3), 3)
    assert not ships(_r(0.5, 0.6, 0.3), 2)
    assert not ships(_r(0.5, 0.6, 0.41), 9)
