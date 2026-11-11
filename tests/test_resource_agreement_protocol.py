from ops_copilot import resource_agreement_protocol as P


def s(answered, opened, rate):
    return {"answered": answered, "refuse_opened": opened, "rates": {"null_pass_rate": rate}}


REF = s(100, 8, 0.109)


def test_frozen_constants():
    assert P.CONFIRM_SEED == 1111 and P.CAL_SEED == 1107 and P.CAL_DRAWS == 3
    assert P.MIN_GAIN_CAL == 2 and P.MIN_GAIN_CONFIRM == 2 and P.MAX_SWAP_RISE == 0.01
    assert list(P.ARMS) == ["shipped", "agree2_known", "agree3_known", "agree2_lone", "agree2_all", "agree3_all"]
    assert P.CONFIRM_FILES[0] == "data/eval/synonym_dev10.jsonl"


def test_pick_largest_gain_among_eligible():
    scores = {"shipped": REF, "agree2_known": s(103, 8, 0.115), "agree3_known": s(102, 8, 0.109),
              "agree2_all": s(106, 9, 0.110)}
    assert P.pick(scores, {}) == "agree2_known"


def test_trap_open_swap_rise_or_wrong_evidence_disqualify():
    assert P.pick({"shipped": REF, "agree2_all": s(110, 9, 0.109)}, {}) is None
    assert P.pick({"shipped": REF, "agree2_all": s(110, 8, 0.125)}, {}) is None
    assert P.pick({"shipped": REF, "agree2_all": s(110, 8, 0.109)}, {"agree2_all": 1}) is None


def test_gain_below_minimum_picks_nothing():
    assert P.pick({"shipped": REF, "agree2_known": s(101, 8, 0.100)}, {}) is None


def test_tie_goes_to_lower_swap_rate_then_order():
    scores = {"shipped": REF, "agree2_known": s(103, 8, 0.112), "agree3_known": s(103, 8, 0.110)}
    assert P.pick(scores, {}) == "agree3_known"


def test_ships_rule():
    assert P.ships(s(104, 3, 0.10), s(101, 3, 0.10), 0, 0)
    assert not P.ships(s(102, 3, 0.10), s(101, 3, 0.10), 0, 0)
    assert not P.ships(s(104, 4, 0.10), s(101, 3, 0.10), 0, 0)
    assert not P.ships(s(104, 3, 0.10), s(101, 3, 0.10), 1, 0)
    assert not P.ships(s(104, 3, 0.12), s(101, 3, 0.10), 0, 0)
    assert not P.ships(s(104, 3, 0.10), s(101, 3, 0.10), 0, 1)
