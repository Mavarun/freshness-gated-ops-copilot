"""Nov 1 cost probes: case-styled and phrase passphrases."""

from __future__ import annotations

import re

from ops_copilot.passphrase import _GEN_CASE_RE, generator_words
from ops_copilot.passphrase_wordlist import (
    CASE_STYLES,
    PHRASE_WORDS,
    cased_passphrases,
    phrase_passphrases,
)


def test_cased_rows_are_deterministic_and_cover_every_style_and_separator():
    a, b = cased_passphrases(5, 64), cased_passphrases(5, 64)
    assert [r.text for r in a] == [r.text for r in b]
    assert {r.separator for r in a} == {"space", "hyphen", "dot", "underscore"}
    secrets = [r.secret for r in a]
    assert any(s.isupper() for s in secrets)  # UPPER rows
    assert any(re.search(r"\b[a-z][A-Z]{2,}", s) for s in secrets)  # inverted rows
    assert len(CASE_STYLES) == 4


def test_cased_rows_only_use_generator_case_shapes_and_eff_words():
    gen = generator_words()
    for r in cased_passphrases(9, 200):
        parts = [p for p in re.split(r"[ ._-]", r.secret) if p and not p.isdigit()]
        assert all(_GEN_CASE_RE.fullmatch(p) for p in parts)
        assert [p.lower() for p in parts] == [w.lower() for w in r.words]
        assert all(w in gen for w in r.words)


def test_phrase_rows_hold_one_inner_function_word_that_is_not_scored():
    gen = generator_words()
    for r in phrase_passphrases(3, 200):
        parts = [p.lower() for p in re.split(r"[ ._-]", r.secret)]
        extra = [p for p in parts if p not in r.words]
        assert len(extra) == 1 and extra[0] in PHRASE_WORDS
        assert parts[0] != extra[0] and parts[-1] != extra[0]
        assert all(w in gen for w in r.words) and 3 <= len(r.words) <= 5


def test_phrase_words_are_off_the_eff_list():
    gen = generator_words()
    assert not [w for w in PHRASE_WORDS if w in gen]
