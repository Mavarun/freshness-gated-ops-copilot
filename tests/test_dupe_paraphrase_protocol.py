from ops_copilot import dupe_paraphrase_protocol as P


def s(answered, opened, rate):
    return {"answered": answered, "refuse_opened": opened, "rates": {"null_pass_rate": rate}}


REF = s(100, 8, 0.036)


def test_frozen_constants():
    assert P.CONFIRM_SEED == 1123 and P.CAL_SEED == 1107 and P.CAL_DRAWS == 3 and P.CONFIRM_DRAWS == 3
    assert P.MIN_GAIN_CAL == 2 and P.MIN_GAIN_CONFIRM == 2 and P.MAX_SWAP_RISE == 0.01
    assert list(P.ARMS) == ["shipped", "strict_known", "strict_lone", "strict_all", "loose_lone", "loose_all"]
    assert P.STRICT == {"dupe_min_cross": 3, "dupe_min_g2": 15.13, "dupe_min_ratio": 2.0}
    assert P.LOOSE == {"dupe_min_cross": 2, "dupe_min_g2": 10.83, "dupe_min_ratio": 1.0}
    assert P.CONFIRM_FILES[0] == "data/eval/synonym_dev10.jsonl"
    assert P.CAL_FILES[-1] == "data/eval/nonkey_dev8.jsonl" and len(P.CAL_FILES) == 6
    assert len(P.SWAP_BASE_FILES) == 5


def test_every_arm_turns_the_knob_on_and_shipped_is_empty():
    assert P.ARMS["shipped"] == {}
    assert all(a["use_dupe_paraphrase"] for n, a in P.ARMS.items() if n != "shipped")


def test_gates_are_textbook_chi_square_values():
    from scipy.stats import chi2

    assert abs(chi2.sf(P.STRICT["dupe_min_g2"], 1) - 1e-4) < 2e-6
    assert abs(chi2.sf(P.LOOSE["dupe_min_g2"], 1) - 1e-3) < 2e-5


def test_pick_largest_gain_among_eligible():
    scores = {"shipped": REF, "strict_known": s(103, 8, 0.040), "strict_lone": s(102, 8, 0.036),
              "loose_all": s(106, 9, 0.036)}
    assert P.pick(scores, {}) == "strict_known"


def test_trap_open_swap_rise_or_wrong_evidence_disqualify():
    assert P.pick({"shipped": REF, "loose_all": s(110, 9, 0.036)}, {}) is None
    assert P.pick({"shipped": REF, "loose_all": s(110, 8, 0.050)}, {}) is None
    assert P.pick({"shipped": REF, "loose_all": s(110, 8, 0.036)}, {"loose_all": 1}) is None


def test_gain_below_minimum_picks_nothing():
    assert P.pick({"shipped": REF, "strict_known": s(101, 8, 0.030)}, {}) is None


def test_tie_goes_to_lower_swap_rate_then_order():
    scores = {"shipped": REF, "strict_known": s(103, 8, 0.040), "strict_lone": s(103, 8, 0.038)}
    assert P.pick(scores, {}) == "strict_lone"
    scores = {"shipped": REF, "strict_known": s(103, 8, 0.038), "strict_lone": s(103, 8, 0.038)}
    assert P.pick(scores, {}) == "strict_known"


def test_ships_rule():
    assert P.ships(s(104, 3, 0.10), s(101, 3, 0.10), 0, 0)
    assert not P.ships(s(102, 3, 0.10), s(101, 3, 0.10), 0, 0)
    assert not P.ships(s(104, 4, 0.10), s(101, 3, 0.10), 0, 0)
    assert not P.ships(s(104, 3, 0.10), s(101, 3, 0.10), 1, 0)
    assert not P.ships(s(104, 3, 0.12), s(101, 3, 0.10), 0, 0)
    assert not P.ships(s(104, 3, 0.10), s(101, 3, 0.10), 0, 1)
