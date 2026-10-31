"""An offline English dictionary: single-word WordNet 3.0 lemmas of every part of speech.

Used by the Oct 31 passphrase ``plain_rule`` to ask "is this a word a person or a
word-list generator would type?" rather than "is this a non-ops token?". The table
is built once from the same SHA-pinned ``wordnet.zip`` as ``wordnet_senses``
(``scripts/build_dictionary_words.py``) and committed as
``data/wordnet/wn_lemmas.txt.gz``: one lower-case alphabetic lemma per line, from
``index.noun``, ``index.verb``, ``index.adj`` and ``index.adv`` plus the irregular
forms of the ``*.exc`` exception lists. No eval text is read.

WordNet stores base forms only, so ``is_word`` adds a small morphy-style suffix
backoff (``-s``, ``-es``, ``-ies``, ``-ed``, ``-ing``, ``-er``, ``-est``, ``-ly``, with
the usual ``e`` / doubled-consonant repairs). It only ever maps a form onto a
lemma that is in the table, so a non-word (``xorg``, ``objectid``) stays out.
"""

from __future__ import annotations

import gzip
import hashlib
from functools import lru_cache
from pathlib import Path

TABLE = Path(__file__).resolve().parents[2] / "data" / "wordnet" / "wn_lemmas.txt.gz"
TABLE_SHA256 = "b1e7059903c567395f8d898fc06f0ffc4c719f810ddc82b9489a5d1aff7a2dbf"
INDEX_FILES = ("index.noun", "index.verb", "index.adj", "index.adv")
EXC_FILES = ("noun.exc", "verb.exc", "adj.exc", "adv.exc")


def parse_lemmas(index_lines, exc_lines=()) -> set[str]:
    """Single-word alphabetic lemmas (lower-case) from WordNet index / exception lines."""
    out: set[str] = set()
    for ln in index_lines:
        if not ln or ln.startswith(" "):
            continue
        w = ln.split(" ", 1)[0].lower()
        if w.isalpha() and w.isascii():
            out.add(w)
    for ln in exc_lines:
        parts = ln.split()
        if parts and parts[0].isalpha() and parts[0].isascii():
            out.add(parts[0].lower())
    return out


@lru_cache(maxsize=1)
def lemmas() -> frozenset[str]:
    raw = gzip.decompress(TABLE.read_bytes())
    if hashlib.sha256(raw).hexdigest() != TABLE_SHA256:
        raise ValueError("wn_lemmas.txt.gz does not match the pinned sha256")
    return frozenset(raw.decode("ascii").split())


def _candidates(w: str):
    yield w
    n = len(w)
    if n > 4 and w.endswith("ies"):
        yield w[:-3] + "y"
    if n > 3 and w.endswith("es"):
        yield w[:-2]
    if n > 3 and w.endswith("s") and not w.endswith("ss"):
        yield w[:-1]
    for suf in ("ed", "ing", "er", "est"):
        if n > len(suf) + 2 and w.endswith(suf):
            stem = w[: -len(suf)]
            yield stem
            yield stem + "e"
            if len(stem) > 2 and stem[-1] == stem[-2]:
                yield stem[:-1]
            if stem.endswith("i"):
                yield stem[:-1] + "y"
    if n > 4 and w.endswith("ly"):
        yield w[:-2]
        if w.endswith("ily"):
            yield w[:-3] + "y"


def is_word(word: str) -> bool:
    """Is ``word`` (any case) a WordNet lemma, or an inflection of one?"""
    w = word.lower()
    if not w.isalpha():
        return False
    table = lemmas()
    return any(c in table for c in _candidates(w))
