"""Cued diceware-style passphrase detector (no copula after the credential noun)."""

from __future__ import annotations

import pytest

from ops_copilot.passphrase import CUED_PASSPHRASE, CuedPassphraseDetector, ops_vocabulary


@pytest.mark.parametrize(
    "text, value",
    [
        ("the deploy token marble meadow lagoon badger stopped working", "marble meadow lagoon badger stopped working"),
        ("the deploy token marble meadow lagoon badger, who rotates it?", "marble meadow lagoon badger"),
        ("log in to grafana with passphrase Lagoon Mosaic Velvet Sonnet 83 please", "Lagoon Mosaic Velvet Sonnet 83"),
        ("the deploy token Canyon-Cobalt-Falcon-Marble-45 stopped working", "Canyon-Cobalt-Falcon-Marble-45"),
        ("token copper.cactus.thistle.cobalt.maple", "copper.cactus.thistle.cobalt.maple"),
        ("api key tulip_badger_otter_prism", "tulip_badger_otter_prism"),
    ],
)
def test_flags_the_value_only(text: str, value: str) -> None:
    m = CUED_PASSPHRASE.search(text)
    assert m is not None and m.group() == value


@pytest.mark.parametrize(
    "text",
    [
        "the token is expired",
        "rotate the token rotation schedule for checkout",
        "api key payments-api-canary-pool",
        "the deploy token for payments-api",
        "the vault token was revoked yesterday",
        "my password",
    ],
)
def test_leaves_ops_text_alone(text: str) -> None:
    assert CUED_PASSPHRASE.search(text) is None


def test_ops_word_passphrase_gap_closed_for_space_runs_only() -> None:
    # three of four words are in the ops-domain vector vocabulary: leaked until Oct 29
    assert {"juniper", "orbit", "copper"} <= ops_vocabulary()
    text = "token juniper orbit copper tundra stopped"
    assert CuedPassphraseDetector(tail="trim", coherence_max=None).search(text) is None
    assert CUED_PASSPHRASE.search(text).group() == "juniper orbit copper tundra stopped"
    # known gap: the same words as a compound
    assert CUED_PASSPHRASE.search("token juniper-orbit-copper-tundra") is None


def test_shipped_defaults_are_the_amended_arm_plus_the_oct30_list_arm() -> None:
    d = CUED_PASSPHRASE
    assert (d.tail, d.coherence_max, d.coherence_compounds) == ("keep", 0.10, False)
    assert (d.wordlist_compounds, d.wordlist_space, d.exempt_identifiers) == ("all4", True, True)


def test_vocabulary_is_injectable_and_subn_counts() -> None:
    d = CuedPassphraseDetector(vocabulary=frozenset(), tail="trim", coherence_max=None)
    out, n = d.subn("[x]", "token alpha beta gamma, and secret delta epsilon zeta")
    assert n == 2 and out == "token [x], and secret [x]"
    assert d.sub("[x]", "") == ""


def test_tail_keep_redacts_a_trailing_ops_word_but_flags_the_same_runs() -> None:
    text = "the deploy token syrup prowling uplifted component stopped working"
    assert CuedPassphraseDetector(tail="trim").search(text).group() == "syrup prowling uplifted"
    keep = CuedPassphraseDetector(tail="keep")
    assert keep.search(text).group() == "syrup prowling uplifted component stopped working"
    for t in ("the token is expired", "rotate the token rotation schedule for checkout", "my password"):
        assert keep.search(t) is None
    # numbers after the kept run stay part of the span
    assert keep.search("passphrase Lagoon Mosaic Velvet Sonnet 83 please").group() == "Lagoon Mosaic Velvet Sonnet 83"


def test_tail_mode_is_validated() -> None:
    with pytest.raises(ValueError):
        CuedPassphraseDetector(tail="drop")


def test_coherence_arm_flags_unrelated_ops_words_only() -> None:
    from ops_copilot.passphrase import mean_pair_cosine

    gap = "token juniper orbit copper tundra stopped"
    arm = CuedPassphraseDetector(coherence_max=0.5, coherence_compounds=True)
    assert CuedPassphraseDetector(coherence_max=None).search(gap) is None
    assert arm.search(gap) is not None
    # a three-word run is below COHERENCE_MIN_WORDS and never uses the arm
    assert arm.search("token juniper orbit copper") is None
    # an unknown word contributes 0 to every pair
    assert mean_pair_cosine(["qqqzz", "xxyyw", "zzkkq", "wwqqz"]) == 0.0
    assert mean_pair_cosine(["server"]) == 0.0
    # coherent ops prose stays below the bar at a tight cut
    assert CuedPassphraseDetector(coherence_max=0.0).search(gap) is None


def test_space_only_coherence_leaves_identifiers_but_flags_space_runs() -> None:
    # the Oct 29 arm, without the Oct 30 exemption list (which would mask the case)
    both = CuedPassphraseDetector(coherence_max=0.10, coherence_compounds=True, exempt_identifiers=False)
    space = CuedPassphraseDetector(coherence_max=0.10, coherence_compounds=False)
    ident = "api key sidecar-mesh-mtls-handshake-budget"
    assert both.search(ident) is not None and space.search(ident) is None
    assert space.search("api key payments-api-canary-pool") is None
    assert space.search("token juniper orbit copper tundra stopped") is not None
    # the ops-word count still flags compounds whatever the switch says
    assert space.search("api key tulip_badger_otter_prism").group() == "tulip_badger_otter_prism"
