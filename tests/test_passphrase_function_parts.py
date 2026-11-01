"""Nov 1 ``function_parts``: phrase passphrases with function words inside a compound."""

from __future__ import annotations

import pytest

from ops_copilot.passphrase import (
    CUED_PASSPHRASE,
    DEFAULT_FUNCTION_PARTS,
    FUNCTION_WORDS,
    MAX_FUNCTION_PARTS,
    CuedPassphraseDetector,
)


def _on() -> CuedPassphraseDetector:
    return CuedPassphraseDetector(function_parts=True)


def test_off_by_default_until_the_protocol_runs():
    assert DEFAULT_FUNCTION_PARTS is False and CUED_PASSPHRASE.function_parts is False
    assert MAX_FUNCTION_PARTS == 2 and {"in", "by", "or", "the", "and"} <= FUNCTION_WORDS


@pytest.mark.parametrize(
    "text, value",
    [
        ("the deploy token turtle_unproven_in_spider_sampling_slug stopped working", "turtle_unproven_in_spider_sampling_slug"),
        ("passphrase Garnish-Unplanted-Underling-By-Uncounted-Chef please", "Garnish-Unplanted-Underling-By-Uncounted-Chef"),
    ],
)
def test_two_letter_function_parts_no_longer_break_the_compound(text, value):
    assert CuedPassphraseDetector().search(text) is None
    assert _on().search(text).group() == value


@pytest.mark.parametrize("name", ["all-in-one-solution", "ab-cd-ef-gh", "ip-to-mac-map", "chicken-and-egg"])
def test_short_non_words_and_short_runs_do_not_become_passphrases(name):
    text = f"token {name}"
    assert (_on().search(text) is None) == (CuedPassphraseDetector().search(text) is None)


def test_too_many_function_parts_is_not_a_phrase_passphrase():
    t = "token ocean-in-the-of-velvet-badger-lamp"
    assert _on().search(t) is None


def test_knob_never_redacts_less():
    for t in ["token marble-meadow-lagoon-badger", "passphrase lagoon mosaic velvet sonnet 83 please",
              "token Appetizer7_Trusting_Unpeeled_Extrude now"]:
        a, b = CuedPassphraseDetector().search(t), _on().search(t)
        if a is not None:
            assert b is not None and b.start() <= a.start() and b.end() >= a.end()


def test_space_runs_are_unchanged():
    t = "log in with passphrase detergent in turtle clerk goofiness please"
    a, b = CuedPassphraseDetector().search(t), _on().search(t)
    assert (a is None and b is None) or a.span() == b.span()
