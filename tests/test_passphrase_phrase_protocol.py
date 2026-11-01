"""The Nov 1 function-parts protocol is fixed before any scored run."""

from __future__ import annotations

from ops_copilot import passphrase_phrase_protocol as F
from ops_copilot import passphrase_shape_protocol as S
from ops_copilot.passphrase import CUED_PASSPHRASE, FUNCTION_WORDS
from ops_copilot.passphrase_wordlist import PHRASE_WORDS


def test_seeds_are_fresh_and_distinct() -> None:
    seeds = [*F.CALIB_SEEDS.values(), *F.CONFIRM_SEEDS.values()]
    assert len(set(seeds)) == len(seeds) == 10
    used = {*S.CALIB_SEEDS.values(), *S.CONFIRM_SEEDS.values(), S.OFFLIST_SEED}
    assert not set(seeds) & used
    plus = {F.CALIB_SEEDS["invented"] + 1, F.CONFIRM_SEEDS["invented"] + 1}
    assert not plus & (set(seeds) | used)
    assert set(F.CALIB_SEEDS) == set(F.CONFIRM_SEEDS) == set(F.PROBES)


def test_arms_pin_the_nov1_shipped_detector() -> None:
    assert F.arms() == [False, True] and F.arm_name(F.SHIPPED) == "shipped"
    d = F.detector(F.SHIPPED)
    keys = ("tail", "coherence_max", "exempt_identifiers", "wordlist_compounds", "attached_digit",
            "digit_guard", "plain_rule", "shape_guards")
    assert {k: getattr(d, k) for k in keys} == {k: getattr(CUED_PASSPHRASE, k) for k in keys}
    assert d.function_parts is False and F.detector(True).function_parts is CUED_PASSPHRASE.function_parts is True


def test_function_words_cover_the_probe_which_is_why_se_is_the_control() -> None:
    assert set(PHRASE_WORDS) <= FUNCTION_WORDS


def _res(arm, phrase=100, other=10, ids_new=0, sent=28, over=0):
    tot = lambda k: {"total": {"rows": 1200, "words": 6000, "leak_words": phrase if k == "phrase" else other,
                               "over_words": 500 + over}}
    return {"arm": F.arm_name(arm), "probe": {k: tot(k) for k in F.PROBES}, "oct13_leak_words": 0,
            "repo_query_changes": 0, "data_ident_new_flags": [],
            "se": {"sent_flagged": sent, "ident_flagged": 166 + ids_new, "ident_new": ids_new}}


def test_checks_and_budgets() -> None:
    base = _res(False, phrase=1250)
    good = _res(True, phrase=600, ids_new=3, sent=33)
    assert all(F.calibration_passes(good, base).values())
    assert not F.confirm_passes(good, base)["se_identifiers"]
    assert not F.confirm_passes(good, base)["se_sentences"]
    assert not F.calibration_passes(_res(True, phrase=1250), base)["gain"]
    assert not F.calibration_passes(_res(True, phrase=600, other=11), base)["no_more_leaks"]
    assert not F.calibration_passes(_res(True, phrase=600, over=601), base)["over_budget"]
