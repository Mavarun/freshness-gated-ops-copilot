"""Oct 31 ``digit_guard``: the glued-digit reading needs one digit on one EFF-list word."""

from __future__ import annotations

import pytest

from ops_copilot.passphrase import CuedPassphraseDetector


def _det(**kw) -> CuedPassphraseDetector:
    return CuedPassphraseDetector(attached_digit=True, digit_guard=True, **kw)


@pytest.mark.parametrize(
    "text, value",
    [
        ("the deploy token Appetizer7_Trusting_Unpeeled_Extrude stopped", "Appetizer7_Trusting_Unpeeled_Extrude"),
        ("token Lip-Smilingly-Igloo3-Bladder-Resurrect", "Lip-Smilingly-Igloo3-Bladder-Resurrect"),
    ],
)
def test_bitwarden_shape_still_flagged(text: str, value: str) -> None:
    assert _det().search(text).group() == value


@pytest.mark.parametrize("name", ["libgl1-mesa-dev", "diffie-hellman-group1-sha1", "ssh2-enum-algos",
                                  "gvfs-udisks2-volume-monitor", "net.ipv4.conf.all"])
def test_versioned_names_are_not_read_as_glued(name: str) -> None:
    # the unguarded Oct 30 knob reads these as glued-digit passphrases or not, the guard never does
    g = _det().search(f"token {name}")
    plain = CuedPassphraseDetector(attached_digit=False).search(f"token {name}")
    assert (g is None) == (plain is None)


def test_two_glued_digits_fall_back_to_the_plain_reading() -> None:
    t = "token cascade5-ranch7-lagoon-mosaic"
    assert CuedPassphraseDetector(attached_digit=True, digit_guard=False).search(t) is not None
    assert _det()._guard_ok("cascade5-ranch7-lagoon-mosaic") is False
    assert (_det().search(t) is None) == (CuedPassphraseDetector().search(t) is None)


def test_guard_needs_the_bare_word_on_the_list() -> None:
    assert _det()._guard_ok("Cascade5 Ranch Lagoon") is True
    assert _det()._guard_ok("libgl1 mesa dev") is False
    assert _det()._guard_ok("Ranch Lagoon Mosaic") is False


def test_guard_never_redacts_less_than_the_plain_patterns() -> None:
    plain = CuedPassphraseDetector()
    for t in ("token porous patronage purveyor lagoon libgl1 stopped",
              "the deploy token marble-meadow-lagoon-badger stopped working",
              "log in with passphrase Lagoon Mosaic Velvet Sonnet 83 please"):
        p = [m.span() for m in plain.finditer(t)]
        g = [m.span() for m in _det().finditer(t)]
        for a, b in p:
            assert any(x <= a and b <= y for x, y in g)


def test_guard_without_attached_digit_is_inert() -> None:
    t = "token Appetizer7_Trusting_Unpeeled_Extrude"
    assert CuedPassphraseDetector(attached_digit=False, digit_guard=True).search(t) is None


def test_shipped_default_is_the_confirmed_guard() -> None:
    from ops_copilot.passphrase import CUED_PASSPHRASE

    d = CuedPassphraseDetector()
    assert (d.attached_digit, d.digit_guard, d.plain_rule) == (True, True, "ops")
    assert (CUED_PASSPHRASE.attached_digit, CUED_PASSPHRASE.digit_guard) == (True, True)
    assert d.search("the deploy token Appetizer7_Trusting_Unpeeled_Extrude stopped") is not None
    assert d.search("token libgl1-mesa-dev") is None
