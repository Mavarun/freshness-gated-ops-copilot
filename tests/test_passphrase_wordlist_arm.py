"""EFF-list membership arm for ops-word passphrases (off by default)."""

from __future__ import annotations

import pytest

from ops_copilot.passphrase import CUED_PASSPHRASE, CuedPassphraseDetector, generator_words, wordlist_match


def test_modes() -> None:
    four = ["elderly", "service", "semantic", "clean"]
    assert set(four) <= generator_words()
    assert wordlist_match(four, "all4") and wordlist_match(four, "but1_4") and wordlist_match(four, "all3")
    assert not wordlist_match(four[:3], "all4") and wordlist_match(four[:3], "all3")
    one_off = four + ["texlive"]
    assert not wordlist_match(one_off, "all4") and wordlist_match(one_off, "but1_4")
    assert not wordlist_match(four, None)
    with pytest.raises(ValueError):
        wordlist_match(four, "all5")
    with pytest.raises(ValueError):
        CuedPassphraseDetector(wordlist_compounds="bogus")


def test_off_by_default_and_closes_the_documented_compound_leak() -> None:
    text = "the deploy token elderly-service-semantic-clean-livable-headphone stopped working"
    assert CUED_PASSPHRASE.wordlist_compounds is None and CUED_PASSPHRASE.wordlist_space is False
    assert CUED_PASSPHRASE.search(text) is None
    on = CuedPassphraseDetector(wordlist_compounds="all4")
    assert on.search(text).group() == "elderly-service-semantic-clean-livable-headphone"
    assert on.search("token Attempt.Rubbing.Essential.Path.42").group() == "Attempt.Rubbing.Essential.Path.42"


@pytest.mark.parametrize(
    "text",
    [
        "api key payments-api-canary-pool",
        "token proxy-cache-path-nginx",
        "secret google-chrome-stable-amd",
    ],
)
def test_identifiers_with_an_off_list_part_stay(text: str) -> None:
    assert CUED_PASSPHRASE.search(text) is None
    assert CuedPassphraseDetector(wordlist_compounds="all4").search(text) is None


def test_space_arm_needs_four_leading_list_words() -> None:
    d = CuedPassphraseDetector(wordlist_space=True, coherence_max=None)
    base = CuedPassphraseDetector(coherence_max=None)
    text = "the deploy token elderly service semantic clean stopped working"
    assert base.search(text) is None
    assert d.search(text).group() == "elderly service semantic clean stopped working"
    # the leading list words decide: three, then an off-list word, is not enough
    assert d.search("token elderly service semantic kubectl clean") is None
    # a stop word ends the run first
    assert d.search("token service clean path is wrong") is None
