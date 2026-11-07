from ops_copilot import swap_null_protocol as P


def _s(rate, answered=10, opened=0):
    return {"rates": {"null_pass_rate": rate}, "answered": answered, "refuse_opened": opened}


def test_protocol_constants_are_frozen():
    assert list(P.ARMS) == ["shipped", "known_off", "sense_all", "sense_known", "credit_rank5"]
    assert (P.CAL_DRAWS, P.CAL_SEED, P.CONFIRM_DRAWS, P.CONFIRM_SEED) == (3, 1107, 3, 2611)
    assert (P.MAX_LOST_CAL, P.MIN_DROP, P.MIN_REL_DROP, P.MAX_LOST_CONFIRM) == (2, 0.05, 0.25, 2)
    assert P.CAL_SEED != P.CONFIRM_SEED


def test_pick_lowest_rate_within_the_loss_budget():
    scores = {"shipped": _s(0.30), "known_off": _s(0.15, 8), "sense_all": _s(0.10, 5), "sense_known": _s(0.15, 9)}
    assert P.pick(scores) == "sense_known"  # sense_all loses 5 > 2; tie at 0.15 goes to fewer lost


def test_pick_needs_the_minimum_drop_and_no_new_opens():
    assert P.pick({"shipped": _s(0.30), "known_off": _s(0.27)}) is None
    assert P.pick({"shipped": _s(0.30), "known_off": _s(0.10, opened=1)}) is None


def test_ship_rule():
    ref = _s(0.30)
    assert P.ships(_s(0.15, 9), ref, 0)
    assert not P.ships(_s(0.15, 7), ref, 0)  # loses 3
    assert not P.ships(_s(0.15, 10), ref, 1)  # opens a trap
    assert not P.ships(_s(0.27, 10), ref, 0)  # drop under 0.05
