"""Nov 1 ``shape_guards``: compounds whose shape no passphrase generator emits."""

from __future__ import annotations

import pytest

from ops_copilot.passphrase import (
    CUED_PASSPHRASE,
    DEFAULT_SHAPE_GUARDS,
    SHAPE_GUARDS,
    CuedPassphraseDetector,
    generator_words,
    host_tlds,
    shape_guard_hits,
)

ALL = SHAPE_GUARDS


def _det(guards=ALL) -> CuedPassphraseDetector:
    return CuedPassphraseDetector(shape_guards=guards)


def test_confirmed_case_and_tld_guards_ship_on_and_stop_stays_off():
    assert DEFAULT_SHAPE_GUARDS == ("case", "tld")
    assert CUED_PASSPHRASE.shape_guards == ("case", "tld")
    assert CUED_PASSPHRASE.search("token csrc.nist.gov") is None
    assert CUED_PASSPHRASE.search("token Windows.System.UserProfile.LockScreen") is None


@pytest.mark.parametrize("part", ["cascade", "Cascade", "CASCADE", "cASCADE", "Cascade5", "cascade7"])
def test_generator_case_shapes_pass_the_case_guard(part):
    assert shape_guard_hits([part, "orbit", "tundra"], "-", ("case",)) == []


@pytest.mark.parametrize("part", ["KernelBase", "AmazonEKS", "LXQt", "VLANs", "JobA", "SWTError", "oResponse"])
def test_internal_case_changes_hit_the_case_guard(part):
    assert shape_guard_hits(["alpha", part, "gamma"], ".", ("case",)) == ["case"]


def test_tld_guard_needs_a_dot_compound_and_skips_generator_words():
    assert "net" in generator_words() and "net" not in host_tlds()
    assert shape_guard_hits(["csrc", "nist", "gov"], ".", ("tld",)) == ["tld"]
    assert shape_guard_hits(["csrc", "nist", "gov"], "-", ("tld",)) == []
    assert shape_guard_hits(["whois", "internic", "net"], ".", ("tld",)) == []


def test_stop_guard_ignores_stop_words_on_the_eff_list():
    assert shape_guard_hits(["chicken", "and", "egg"], "-", ("stop",)) == ["stop"]
    assert "many" in generator_words()
    assert shape_guard_hits(["one", "some", "many"], "-", ("stop",)) == ["stop"]  # "some" is not on the list
    assert shape_guard_hits(["very", "much", "used"], "-", ("stop",)) == []


def test_trailing_number_part_is_ignored():
    assert shape_guard_hits(["Lagoon", "Mosaic", "Velvet", "83"], "-", ALL) == []


def test_unknown_guard_rejected():
    with pytest.raises(ValueError):
        shape_guard_hits(["a", "b"], "-", ("vowels",))
    with pytest.raises(ValueError):
        CuedPassphraseDetector(shape_guards=("vowels",))


@pytest.mark.parametrize(
    "name",
    ["BTRFS_FIRST_FREE_OBJECTID", "csrc.nist.gov", "chicken-and-egg", "org.eclipse.swt.SWTError"],
)
def test_guards_only_ever_remove_flags(name):
    text = f"token {name}"
    if _det().search(text) is not None:
        assert CuedPassphraseDetector().search(text) is not None


@pytest.mark.parametrize(
    "secret",
    ["marble-meadow-lagoon-badger", "Lagoon.Mosaic.Velvet.Sonnet.83", "CASCADE_ORBIT_TUNDRA_BADGER",
     "cascade-ORBIT-tundra-BADGER", "Appetizer7_Trusting_Unpeeled_Extrude"],
)
def test_generator_output_flagged_the_same_with_and_without_guards(secret):
    text = f"the deploy token {secret} stopped working"
    base = CuedPassphraseDetector(attached_digit=True, digit_guard=True).search(text)
    guarded = CuedPassphraseDetector(attached_digit=True, digit_guard=True, shape_guards=ALL).search(text)
    assert (base is None) == (guarded is None)
    if base is not None:
        assert base.span() == guarded.span()


def test_space_runs_are_untouched():
    text = "log in with passphrase lagoon mosaic velvet sonnet please"
    a, b = CuedPassphraseDetector().search(text), _det().search(text)
    assert (a is None) == (b is None)
