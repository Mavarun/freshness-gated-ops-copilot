"""Cued diceware-style passphrase detector (no copula after the credential noun)."""

from __future__ import annotations

import pytest

from ops_copilot.passphrase import CUED_PASSPHRASE, CuedPassphraseDetector, ops_vocabulary


@pytest.mark.parametrize(
    "text, value",
    [
        ("the deploy token marble meadow lagoon badger stopped working", "marble meadow lagoon badger"),
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


def test_known_gap_passphrase_of_ops_words() -> None:
    # three of four words are in the ops-domain vector vocabulary: documented leak
    assert {"juniper", "orbit", "copper"} <= ops_vocabulary()
    assert CUED_PASSPHRASE.search("token juniper orbit copper tundra stopped") is None


def test_vocabulary_is_injectable_and_subn_counts() -> None:
    d = CuedPassphraseDetector(vocabulary=frozenset())
    out, n = d.subn("[x]", "token alpha beta gamma, and secret delta epsilon zeta")
    assert n == 2 and out == "token [x], and secret [x]"
    assert d.sub("[x]", "") == ""
