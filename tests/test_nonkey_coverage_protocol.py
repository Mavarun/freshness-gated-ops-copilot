from ops_copilot import nonkey_coverage_protocol as P


def _s(passed, n=100, answered=50, opened=0):
    return {"passed": passed, "n_swaps": n, "answered": answered, "refuse_opened": opened,
            "rates": {"null_pass_rate": passed / n}}


def test_frozen_constants():
    assert list(P.ARMS) == ["shipped", "all", "corpus", "idf_q25", "idf_q50", "cov_065"]
    assert (P.CAL_SEED, P.CONFIRM_SEED, P.CAL_DRAWS, P.CONFIRM_DRAWS) == (1107, 1109, 3, 3)
    assert (P.MAX_LOST_CAL, P.MIN_DROP, P.MIN_REL_DROP, P.MAX_LOST_CONFIRM) == (2, 0.03, 0.25, 2)
    assert P.DEV8_FILE in P.CONFIRM_FILES and P.ARMS["shipped"] == {}


def test_pick_lowest_eligible_rate():
    scores = {"shipped": _s(11), "all": _s(2, answered=45), "corpus": _s(4, answered=49), "idf_q25": _s(5)}
    assert P.pick(scores) == "corpus"  # 'all' loses 5 rows


def test_pick_needs_min_drop_and_no_new_opens():
    assert P.pick({"shipped": _s(11), "corpus": _s(9)}) is None
    assert P.pick({"shipped": _s(11), "corpus": _s(1, opened=1)}) is None


def test_ties_go_to_fewer_lost_then_earlier_arm():
    scores = {"shipped": _s(11), "all": _s(4, answered=49), "corpus": _s(4, answered=50), "idf_q25": _s(4)}
    assert P.pick(scores) == "corpus"


def test_ship_rule():
    ref = _s(15)
    assert P.ships(_s(10), ref, 0, 1, 1)
    assert not P.ships(_s(13), ref, 0, 0, 1)  # under 0.03 absolute
    assert not P.ships(_s(10, answered=47), ref, 0, 0, 0)  # 3 rows lost
    assert not P.ships(_s(10), ref, 1, 0, 0)  # attribute trap opens
    assert not P.ships(_s(10), ref, 0, 2, 1)  # more topic traps than shipped
    assert not P.ships(_s(0), _s(0), 0, 0, 0)  # nothing to drop
