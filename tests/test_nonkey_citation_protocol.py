"""The frozen citation-aware non-key protocol: arms, files, seeds and the pick/ship rules."""

from ops_copilot import nonkey_citation_protocol as P
from ops_copilot import nonkey_parts_protocol as N10


def _s(rate, answered=100, opened=0):
    return {"rates": {"null_pass_rate": rate}, "answered": answered, "refuse_opened": opened}


def _c(budget=0, wrong=()):
    return {"budget_lost": budget, "new_wrong": list(wrong)}


def test_frozen_constants_reuse_the_unrun_nov10_confirm():
    assert P.ARMS == N10.ARMS and P.REFERENCE_ONLY == ("all",)
    assert P.CONFIRM_SEED == 1110 and P.CAL_SEED == 1107 and P.CAL_DRAWS == 3 == P.CONFIRM_DRAWS
    assert P.CAL_FILES == N10.CAL_FILES and P.CONFIRM_FILES == N10.CONFIRM_FILES
    assert P.CONFIRM_FILES[0] == P.DEV9_FILE and P.DEV9_FILE not in P.CAL_FILES
    assert P.MAX_LOST_CAL == 2 == P.MAX_LOST_CONFIRM and P.MIN_DROP == 0.03 and P.MIN_REL_DROP == 0.25
    assert P.EXPECTED_PICK == "all_hyphen"


def test_budget_count_not_decision_count_decides_eligibility():
    ref = _s(0.10)
    # 3 decision losses, one of them a fixed wrong-evidence answer -> budget 2 -> eligible
    assert P.eligible(_s(0.04, answered=97), ref, _c(budget=2))
    assert not P.eligible(_s(0.04), ref, _c(budget=3))
    assert not P.eligible(_s(0.04), ref, _c(wrong=["d2-13"]))
    assert not P.eligible(_s(0.04, opened=1), ref, _c())


def test_reference_arm_is_never_picked_and_min_drop_applies():
    scores = {"shipped": _s(0.10), "all": _s(0.01), "all_hyphen": _s(0.05)}
    cites = {n: _c() for n in scores}
    assert P.pick(scores, cites) == "all_hyphen"
    assert P.pick({"shipped": _s(0.10), "all_hyphen": _s(0.08)}, {"all_hyphen": _c()}) is None


def test_ties_go_to_lower_budget_then_earlier_arm():
    s = {"shipped": _s(0.10), "all_hyphen": _s(0.04), "all_joined": _s(0.04), "corpus_hyphen": _s(0.04)}
    assert P.pick(s, {"all_hyphen": _c(2), "all_joined": _c(1), "corpus_hyphen": _c(1)}) == "all_joined"
    assert P.pick(s, {"all_hyphen": _c(2), "all_joined": _c(2), "corpus_hyphen": _c(2)}) == "all_hyphen"


def test_ship_rule():
    ref = _s(0.10)
    assert P.ships(_s(0.05), ref, _c(2), 0, 2, 3)
    assert not P.ships(_s(0.05), ref, _c(3), 0, 2, 3)  # budget
    assert not P.ships(_s(0.05), ref, _c(0, ["d9-01"]), 0, 2, 3)  # new wrong evidence
    assert not P.ships(_s(0.05), ref, _c(), 1, 2, 3)  # attribute trap
    assert not P.ships(_s(0.05), ref, _c(), 0, 4, 3)  # more topic traps
    assert not P.ships(_s(0.08), ref, _c(), 0, 0, 3)  # drop 0.02
    assert not P.ships(_s(0.16), _s(0.20), _c(), 0, 0, 3)  # 0.04 absolute but only 20% relative
