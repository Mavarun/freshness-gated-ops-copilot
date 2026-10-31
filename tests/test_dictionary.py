"""The committed WordNet 3.0 lemma table and its suffix backoff."""

from __future__ import annotations

import gzip
import hashlib

import pytest

from ops_copilot import dictionary as D


def test_table_is_pinned_sorted_lower_alpha() -> None:
    raw = gzip.decompress(D.TABLE.read_bytes())
    assert hashlib.sha256(raw).hexdigest() == D.TABLE_SHA256
    words = raw.decode("ascii").split()
    assert words == sorted(words) and len(words) == len(set(words)) == 82302
    assert all(w.isalpha() and w == w.lower() for w in words)


def test_parse_lemmas_keeps_single_alpha_words() -> None:
    idx = ["  1 This software and database", "glacier n 1 1 @ 1 0 09289331",
           "ice_age n 1 1", "3-d a 1", "Run v 3", "café n 1"]
    exc = ["geese goose", "ran run", "a_cappella x"]
    assert D.parse_lemmas(idx, exc) == {"glacier", "run", "geese", "ran"}


@pytest.mark.parametrize("w", ["badger", "badgers", "Meadows", "stopped", "running", "bigger", "quickly",
                               "happily", "ponies", "boxes", "baked", "geese"])
def test_forms_of_lemmas_are_words(w: str) -> None:
    assert D.is_word(w)


@pytest.mark.parametrize("w", ["xorg", "libinput", "btrfs", "objectid", "clsctx", "inproc", "zorbak", "bafiku", "ab1", ""])
def test_non_words(w: str) -> None:
    assert not D.is_word(w)


def test_backoff_only_lands_on_table_entries() -> None:
    table = D.lemmas()
    for w in ("badgers", "stopped", "happily"):
        assert any(c in table for c in D._candidates(w))
    assert not any(c in table for c in D._candidates("objectids"))


def test_wordnet_notice_names_both_tables_and_carries_the_licence() -> None:
    notice = (D.TABLE.parent / "NOTICE.md").read_text()
    assert "wn_lemmas.txt.gz" in notice and "wn_noun_neighbours.json.gz" in notice
    assert "WordNet 3.0 Copyright 2006 by Princeton University.  All rights reserved." in notice
    assert 'THIS SOFTWARE AND DATABASE IS PROVIDED "AS IS"' in notice
    # the notice is scanned by passphrase.known_identifiers; it must not add exempt names
    from ops_copilot.passphrase import _IDENT_RE

    assert not list(_IDENT_RE.finditer(notice.lower()))
