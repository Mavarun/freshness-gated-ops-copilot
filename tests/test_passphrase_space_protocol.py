"""The Nov 4 space-bridge protocol is fixed before any scored run."""

from __future__ import annotations

from ops_copilot import passphrase_phrase_protocol as P
from ops_copilot import passphrase_shape_protocol as S
from ops_copilot import passphrase_space_protocol as F
from ops_copilot.passphrase import CUED_PASSPHRASE
from ops_copilot.passphrase_wordlist import CONNECTIVE_WORDS, PHRASE_WORDS


def test_seeds_are_fresh_and_distinct() -> None:
    seeds = [*F.CALIB_SEEDS.values(), *F.CONFIRM_SEEDS.values()]
    assert len(set(seeds)) == len(seeds) == 12
    used = {*S.CALIB_SEEDS.values(), *S.CONFIRM_SEEDS.values(), S.OFFLIST_SEED,
            *P.CALIB_SEEDS.values(), *P.CONFIRM_SEEDS.values()}
    plus = {s + 1 for s in used}  # the invented probe uses seed and seed + 1
    assert not set(seeds) & (used | plus)
    assert not {F.CALIB_SEEDS["invented"] + 1, F.CONFIRM_SEEDS["invented"] + 1} & set(seeds)
    assert set(F.CALIB_SEEDS) == set(F.CONFIRM_SEEDS) == set(F.PROBES)


def test_grid_starts_at_the_shipped_detector_and_arms_pin_the_nov1_knobs() -> None:
    assert F.arms()[0] == F.SHIPPED and F.arm_name(F.SHIPPED) == "shipped"
    assert [F.arm_name(a) for a in F.arms()] == ["shipped", "prep/1", "prep/2", "func/2", "stop/2"]
    d = F.detector(F.SHIPPED)
    keys = ("tail", "coherence_max", "exempt_identifiers", "wordlist_compounds", "attached_digit",
            "digit_guard", "plain_rule", "shape_guards", "function_parts")
    assert {k: getattr(d, k) for k in keys} == {k: getattr(CUED_PASSPHRASE, k) for k in keys}
    assert d.space_bridge is None and F.detector(("func", 2)).space_bridge == "func"
    assert F.detector(("prep", 1)).space_bridge_max == 1


def test_probe_words_are_the_documented_split() -> None:
    from ops_copilot.passphrase import PREP_WORDS, bridge_words

    assert not set(PHRASE_WORDS) <= PREP_WORDS  # my / you / is are not on the prep list
    assert set(PHRASE_WORDS) <= bridge_words("func")
    assert not set(CONNECTIVE_WORDS) & bridge_words("stop")
    rows = F.probe_rows("connective", F.CALIB_SEEDS["connective"], 40)
    assert len(rows) == 40 and F.probe_rows("phrase", 1, 5) == F.probe_rows("phrase", 1, 5)


def _res(arm, phrase=100, other=10, ids_new=0, sent=28, over=0, conn=None):
    tot = lambda k: {"total": {"rows": 1200, "words": 6000, "over_words": 500 + over,
                               "leak_words": phrase if k == "phrase" else (other if conn is None or k != "connective" else conn)}}
    return {"arm": F.arm_name(arm), "probe": {k: tot(k) for k in F.PROBES}, "oct13_leak_words": 0,
            "repo_query_changes": 0, "data_ident_new_flags": [],
            "se": {"sent_flagged": sent, "ident_flagged": 166 + ids_new, "ident_new": ids_new}}


def test_checks_and_budgets() -> None:
    base = _res(F.SHIPPED, phrase=500)
    good = _res(("prep", 2), phrase=100, sent=33, ids_new=3)
    assert all(F.calibration_passes(good, base).values())
    assert not F.confirm_passes(good, base)["se_sentences"] and not F.confirm_passes(good, base)["se_identifiers"]
    assert not F.calibration_passes(_res(("prep", 2), phrase=500), base)["gain"]
    assert not F.calibration_passes(_res(("prep", 2), phrase=100, conn=11), base)["no_more_leaks"]
    assert not F.calibration_passes(_res(("prep", 2), phrase=100, over=601), base)["over_budget"]


def test_pick_is_the_safe_arm_with_the_fewest_phrase_leaks_then_grid_order() -> None:
    base = _res(F.SHIPPED, phrase=500)
    rs = [base, _res(("prep", 1), phrase=300), _res(("prep", 2), phrase=200), _res(("func", 2), phrase=200),
          _res(("stop", 2), phrase=100, sent=40)]
    assert F.pick(rs, base)["arm"] == "prep/2"  # stop/2 is unsafe; prep/2 beats func/2 on the tie
    assert F.pick([base, _res(("prep", 1), phrase=500)], base) is None
