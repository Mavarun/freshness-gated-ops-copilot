"""Bitwarden-style glued digit ("Cascade5") in cued passphrases (knob, default off)."""

from __future__ import annotations

import pytest

from ops_copilot.passphrase import CUED_DIGIT_RE, CUED_RE, CuedPassphraseDetector


@pytest.mark.parametrize(
    "text, value",
    [
        ("the deploy token porous patronage cascade5 purveyor stopped working", "porous patronage cascade5 purveyor stopped working"),
        ("the deploy token Appetizer7_Trusting_Unpeeled_Extrude stopped", "Appetizer7_Trusting_Unpeeled_Extrude"),
        ("token Lip-Smilingly-Igloo3-Bladder-Resurrect", "Lip-Smilingly-Igloo3-Bladder-Resurrect"),
    ],
)
def test_glued_digit_runs_are_flagged_with_the_knob(text: str, value: str) -> None:
    assert CuedPassphraseDetector(attached_digit=False).search(text) is None
    assert CuedPassphraseDetector(attached_digit=True).search(text).group() == value


@pytest.mark.parametrize(
    "text",
    ["the token is expired2", "api key payments-api-canary-pool", "rotate the token rotation schedule for checkout2",
     "the deploy token for payments-api2", "api key sidecar-mesh-mtls-handshake-budget"],
)
def test_ops_text_still_alone(text: str) -> None:
    assert CuedPassphraseDetector(attached_digit=True).search(text) is None


def test_digit_regex_is_a_superset_and_word_checks_drop_one_digit() -> None:
    for t in ("token alpha beta gamma", "token a-b-c", "token alpha-beta-gamma-12"):
        assert (CUED_RE.search(t) is None) or CUED_DIGIT_RE.search(t) is not None
    d = CuedPassphraseDetector(attached_digit=True)
    assert d._bare("cascade5") == "cascade" and d._bare("ab12") == "ab12" and d._bare("7") == "7"
    assert CuedPassphraseDetector(attached_digit=False)._bare("cascade5") == "cascade5"
    # two glued digits are not the Bitwarden shape: the run stops before the word
    assert CUED_DIGIT_RE.search("token porous patronage cascade55 purveyor").group("val") == "porous patronage"
