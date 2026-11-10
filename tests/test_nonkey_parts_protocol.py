"""The frozen compound-parts protocol: arms, files, seeds and the pick/ship rules."""

from ops_copilot import nonkey_parts_protocol as P


def _s(rate, answered=100, opened=0):
    return {"rates": {"null_pass_rate": rate}, "answered": answered, "refuse_opened": opened}


def test_frozen_constants():
    assert P.CONFIRM_SEED == 1110 and P.CAL_SEED == 1107 and P.CAL_DRAWS == 3 == P.CONFIRM_DRAWS
    assert P.MAX_LOST_CAL == 2 == P.MAX_LOST_CONFIRM and P.MIN_DROP == 0.03 and P.MIN_REL_DROP == 0.25
    assert P.DEV8_FILE in P.CAL_FILES and P.DEV8_FILE not in P.SWAP_BASE_FILES
    assert P.CONFIRM_FILES[0] == P.DEV9_FILE and P.DEV9_FILE not in P.CAL_FILES
    assert list(P.ARMS) == ["shipped", "all", "all_hyphen", "all_joined", "corpus_hyphen"]


def test_reference_arm_is_never_picked():
    scores = {"shipped": _s(0.10), "all": _s(0.01), "all_hyphen": _s(0.05)}
    assert P.pick(scores) == "all_hyphen"


def test_pick_needs_min_drop_and_eligibility():
    assert P.pick({"shipped": _s(0.10), "all_hyphen": _s(0.08)}) is None
    assert P.pick({"shipped": _s(0.10), "all_hyphen": _s(0.02, answered=97)}) is None
    assert P.pick({"shipped": _s(0.10), "all_hyphen": _s(0.02, opened=1)}) is None


def test_pick_ties_go_to_fewer_lost_then_earlier_arm():
    s = {"shipped": _s(0.10), "all_hyphen": _s(0.04, answered=99), "all_joined": _s(0.04, answered=100),
         "corpus_hyphen": _s(0.04, answered=100)}
    assert P.pick(s) == "all_joined"


def test_ship_rule():
    ref = _s(0.10)
    assert P.ships(_s(0.05, answered=98), ref, 0, 2, 3)
    assert not P.ships(_s(0.05, answered=97), ref, 0, 2, 3)  # 3 lost
    assert not P.ships(_s(0.05), ref, 1, 2, 3)  # attribute trap
    assert not P.ships(_s(0.05), ref, 0, 4, 3)  # more topic traps
    assert not P.ships(_s(0.08), ref, 0, 0, 3)  # drop 0.02
