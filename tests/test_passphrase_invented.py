"""Invented-word passphrases: the cost control of the Oct 31 ``plain_rule`` knob."""

from __future__ import annotations

import pytest

from ops_copilot.passphrase import in_dictionary, is_cv_word, ops_vocabulary
from ops_copilot.passphrase_wordlist import (
    INVENTED_POOL_SIZE,
    invented_passphrases,
    invented_words,
)


@pytest.mark.parametrize("shape", ["cv", "cvc"])
def test_pool_is_fixed_and_outside_every_list(shape: str) -> None:
    ws = invented_words(shape)
    assert len(ws) == len(set(ws)) == INVENTED_POOL_SIZE
    ops = ops_vocabulary()
    assert not any(w in ops or in_dictionary(w) for w in ws)
    invented_words.cache_clear()
    assert invented_words(shape) == ws


def test_shapes_split_on_the_cv_rule() -> None:
    assert all(is_cv_word(w) for w in invented_words("cv"))
    assert not any(is_cv_word(w) for w in invented_words("cvc"))


def test_rows_alternate_shapes_and_are_seeded() -> None:
    rows = invented_passphrases(5, 40)
    assert len(rows) == 40
    cv = set(invented_words("cv"))
    assert all((set(r.words) <= cv) == (i % 2 == 0) for i, r in enumerate(rows))
    assert [r.text for r in rows] == [r.text for r in invented_passphrases(5, 40)]
    assert [r.text for r in rows] != [r.text for r in invented_passphrases(6, 40)]


def test_bad_shape_raises() -> None:
    with pytest.raises(ValueError):
        invented_words("ccv")
