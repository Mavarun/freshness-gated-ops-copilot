"""Nov 4 ``space_bridge``: space-joined phrase passphrases with a function word inside."""

from __future__ import annotations

import pytest

from ops_copilot.passphrase import (
    CUED_PASSPHRASE,
    FUNCTION_WORDS,
    PREP_WORDS,
    CuedPassphraseDetector,
    bridge_words,
)
from ops_copilot.text import STOPWORDS


def _det(kind="prep", mx=2) -> CuedPassphraseDetector:
    return CuedPassphraseDetector(space_bridge=kind, space_bridge_max=mx)


def test_bridge_lists_nest_and_are_validated():
    assert bridge_words(None) == frozenset()
    assert bridge_words("prep") == PREP_WORDS < FUNCTION_WORDS == bridge_words("func") < bridge_words("stop")
    assert STOPWORDS <= bridge_words("stop")
    with pytest.raises(ValueError):
        bridge_words("everything")
    with pytest.raises(ValueError):
        CuedPassphraseDetector(space_bridge_max=-1)


@pytest.mark.parametrize(
    "text, value",
    [
        ("log in with passphrase detergent in turtle clerk goofiness please", "detergent in turtle clerk goofiness"),
        ("deploy token ocean in velvet by badger now", "ocean in velvet by badger"),
        ("vault passphrase Lagoon of Mosaic Velvet Sonnet 83 please", "Lagoon of Mosaic Velvet Sonnet 83"),
    ],
)
def test_a_function_word_no_longer_ends_the_space_run(text, value):
    assert CuedPassphraseDetector(space_bridge=None).search(text) is None
    assert _det().search(text).group() == value


def test_a_bridge_word_is_never_first_last_or_doubled_and_the_cap_holds():
    d = _det()
    # trailing bridge word is not part of the span
    assert d.search("token ocean velvet badger sample in").group() == "ocean velvet badger sample"
    # two bridge words in a row end the run at the first
    assert d.search("token ocean velvet badger in the lamp").group() == "ocean velvet badger"
    # the cap: a third bridge word ends the run
    assert _det(mx=2).search("token ocean in velvet by badger or lamp").group() == "ocean in velvet by badger"
    assert _det(mx=1).search("token ocean in velvet badger by lamp sample").group() == "ocean in velvet badger"
    assert _det(mx=0).search("token ocean in velvet by badger") is None


def test_bridge_words_are_left_out_of_the_word_test():
    # Two words around one bridge word is still too short to be a passphrase.
    assert _det().search("passphrase ocean in velvet please") is None


@pytest.mark.parametrize("kind", ["prep", "func", "stop"])
def test_prose_after_a_credential_noun_stays_unflagged(kind):
    for t in ["the password is at the end of the line", "reset the token for example later",
              "token is in the cache and the pin is wrong", "secret of the universe"]:
        assert _det(kind).search(t) is None


def test_copula_is_a_bridge_word_only_from_func_up():
    t = "passphrase ocean is velvet badger sample now"
    assert _det("prep").search(t) is None
    assert _det("func").search(t).group() == "ocean is velvet badger sample"


@pytest.mark.parametrize(
    "text",
    ["log in with passphrase detergent in turtle clerk goofiness please", "token marble meadow lagoon badger",
     "deploy token ocean in velvet by badger now", "token marble-meadow-lagoon-badger", "pin 4821"],
)
def test_knob_never_redacts_less(text):
    a, b = CuedPassphraseDetector(space_bridge=None).search(text), _det("stop").search(text)
    if a is not None:
        assert b is not None and b.start() <= a.start() and b.end() >= a.end()


def test_off_by_default_until_its_protocol_runs():
    assert CUED_PASSPHRASE.space_bridge is None
    assert CUED_PASSPHRASE.search("token ocean in velvet by badger now") is None


# ---- Nov 4, second reading: ``space_bridge_rule`` (list words only) ----

def _eff(rule="eff3", kind="func", mx=2) -> CuedPassphraseDetector:
    return CuedPassphraseDetector(space_bridge=kind, space_bridge_max=mx, space_bridge_rule=rule)


def test_rule_is_validated_and_defaults_to_plain():
    from ops_copilot.passphrase import DEFAULT_SPACE_BRIDGE_RULE, SPACE_BRIDGE_RULES

    assert SPACE_BRIDGE_RULES == ("plain", "eff3", "eff4") and DEFAULT_SPACE_BRIDGE_RULE == "plain"
    with pytest.raises(ValueError):
        CuedPassphraseDetector(space_bridge_rule="eff5")


def test_eff_rule_reads_a_bridged_run_only_when_every_content_word_is_on_the_list():
    t = "log in with passphrase detergent in turtle clerk goofiness please"
    assert _eff("eff3").search(t).group() == "detergent in turtle clerk goofiness"
    assert _eff("eff4").search(t).group() == "detergent in turtle clerk goofiness"
    # prose with unusual words that the plain count flags is not read by the eff rule
    prose = "password managers lead to better outcomes"
    assert _det("func").search(prose) is not None
    assert _eff("eff3").search(prose) is None and _eff("eff4").search(prose) is None


def test_eff_rule_cuts_at_the_first_off_list_word_and_keeps_a_trailing_number():
    assert _eff().search("passphrase detergent in turtle clerk zzyzx extra").group() == "detergent in turtle clerk"
    assert _eff().search("passphrase detergent in turtle clerk 83 now").group() == "detergent in turtle clerk 83"
    # a bridge word is never left dangling at the end of the cut
    assert _eff().search("passphrase detergent turtle clerk by zzyzx").group() == "detergent turtle clerk"


def test_eff_thresholds_are_three_and_four_content_words():
    t = "passphrase detergent in turtle clerk please"
    assert _eff("eff3").search(t).group() == "detergent in turtle clerk"
    assert _eff("eff4").search(t) is None or _eff("eff4").search(t).group() != "detergent in turtle clerk"


def test_eff_rule_needs_a_bridge_word_so_it_never_changes_unbridged_runs():
    t = "passphrase detergent turtle clerk goofiness please"
    a, b = _det("func").search(t), _eff("eff3").search(t)
    assert (a is None) == (b is None) and (a is None or a.span() == b.span())


@pytest.mark.parametrize("rule", ["eff3", "eff4"])
def test_eff_rule_never_redacts_less(rule):
    for t in ["log in with passphrase detergent in turtle clerk goofiness please", "token marble meadow lagoon badger",
              "token detergent turtle clerk", "token marble-meadow-lagoon-badger"]:
        a, b = CuedPassphraseDetector(space_bridge=None).search(t), _eff(rule).search(t)
        if a is not None:
            assert b is not None and b.start() <= a.start() and b.end() >= a.end()
