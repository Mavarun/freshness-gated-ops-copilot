"""Oct 31 ``plain_rule`` knob: a plain word must be a dictionary (or CV-invented) word."""

from __future__ import annotations

import pytest

from ops_copilot.passphrase import (
    CuedPassphraseDetector,
    generator_words,
    in_dictionary,
    is_cv_word,
    plain_word_test,
)


def test_dictionary_holds_the_eff_list_and_wordnet_lemmas() -> None:
    assert all(in_dictionary(w) for w in sorted(generator_words())[:500])
    assert all(in_dictionary(w) for w in ("glacier", "Lantern", "badger", "stopped", "running"))
    assert not any(in_dictionary(w) for w in ("xorg", "libinput", "btrfs", "objectid", "a1b"))


@pytest.mark.parametrize("w, ok", [("bafiku", True), ("zolemi", True), ("abaku", False), ("bak", False),
                                   ("zorbak", False), ("Bafiku", True), ("ba2iku", False)])
def test_cv_word_shape(w: str, ok: bool) -> None:
    assert is_cv_word(w) is ok


def test_plain_predicates() -> None:
    is_ops = {"service", "config"}.__contains__
    assert plain_word_test("ops", is_ops)("xorg") is True
    assert plain_word_test("dict", is_ops)("xorg") is False
    assert plain_word_test("dict", is_ops)("glacier") is True
    assert plain_word_test("dict", is_ops)("service") is False
    assert plain_word_test("dict_cv", is_ops)("bafiku") is True
    assert plain_word_test("dict", is_ops)("bafiku") is False
    with pytest.raises(ValueError):
        plain_word_test("nope", is_ops)


@pytest.mark.parametrize("name", ["xserver-xorg-input-libinput", "BTRFS_FIRST_FREE_OBJECTID", "CLSCTX_INPROC_SERVER"])
def test_non_word_identifiers_stop_counting(name: str) -> None:
    assert CuedPassphraseDetector(plain_rule="ops").search(f"token {name}") is not None
    assert CuedPassphraseDetector(plain_rule="dict").search(f"token {name}") is None


@pytest.mark.parametrize("text", ["the deploy token marble-meadow-lagoon-badger stopped working",
                                  "token Glacier.Nectar.Raven.Tulip.42"])
def test_dictionary_passphrases_still_flagged(text: str) -> None:
    for rule in ("dict", "dict_cv"):
        assert CuedPassphraseDetector(plain_rule=rule).search(text) is not None


def test_invented_words_need_the_cv_rule() -> None:
    t = "token bafiku-zolemi-kurato-pinesa"
    assert CuedPassphraseDetector(plain_rule="ops").search(t) is not None
    assert CuedPassphraseDetector(plain_rule="dict").search(t) is None
    assert CuedPassphraseDetector(plain_rule="dict_cv").search(t) is not None


def test_scope_compounds_leaves_space_runs_alone() -> None:
    t = "token xorg libinput objectid btrfs stopped"
    ship = CuedPassphraseDetector(plain_rule="ops").search(t)
    comp = CuedPassphraseDetector(plain_rule="dict", plain_scope="compounds").search(t)
    assert (ship is None) == (comp is None)
    if ship is not None:
        assert ship.group() == comp.group()
    assert CuedPassphraseDetector(plain_rule="dict", plain_scope="all", coherence_max=None,
                                  wordlist_space=False).search(t) is None


def test_bad_knob_values_raise() -> None:
    with pytest.raises(ValueError):
        CuedPassphraseDetector(plain_rule="x")
    with pytest.raises(ValueError):
        CuedPassphraseDetector(plain_scope="x")


def test_default_is_the_oct30_rule() -> None:
    d = CuedPassphraseDetector()
    assert d.plain_rule == "ops" and d.plain_scope == "compounds"
