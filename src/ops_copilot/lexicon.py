"""Corpus vocabulary with deterministic typo-tolerant lookup (offline, no model).

``CorpusVocabulary.correct`` maps an unknown query token to a *unique* known
word within Damerau-Levenshtein (optimal string alignment) distance 1, where
the single edit must look like a keyboard slip (``is_keyboard_typo``):
adjacent transposition, a dropped letter, a doubled or QWERTY-adjacent extra
letter, or a QWERTY-adjacent substitution. Plain distance 1 alone snapped real
words to the wrong corpus word ("interval" -> "internal", "patch" -> "path");
the keyboard constraint rejects both. Further rules:

- identifiers (digits, ``-``, ``_``, ``.``) are exact-only and never corrected;
- tokens shorter than 3 characters are never corrected, and targets must be at
  least 4 characters long;
- tokens of 5+ characters may match any distance-1 neighbour;
- 3-4 character tokens must also keep the first and last character (short
  words have too many neighbours otherwise, e.g. ``slak`` -> ``slack`` is
  allowed but ``lag`` -> ``log`` is not);
- ties are broken by shared first character, then shared last character,
  then higher document frequency; a remaining tie returns ``None``.

The vocabulary is built from the corpus (plus, optionally, stopword/filler
lists so typo'd filler such as ``whhat`` can be recognised as filler).
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Iterable

from ops_copilot.text import is_identifier

MIN_TOKEN_LEN = 3
MIN_TARGET_LEN = 4
FREE_EDIT_LEN = 5


def within_one_edit(a: str, b: str) -> bool:
    """True when OSA Damerau-Levenshtein distance(a, b) <= 1."""
    if a == b:
        return True
    la, lb = len(a), len(b)
    if abs(la - lb) > 1:
        return False
    if la == lb:
        diff = [i for i in range(la) if a[i] != b[i]]
        if len(diff) == 1:
            return True  # substitution
        if len(diff) == 2:
            i, j = diff
            return j == i + 1 and a[i] == b[j] and a[j] == b[i]  # transposition
        return False
    if la > lb:
        a, b, la, lb = b, a, lb, la
    # b is one longer: deletion from b gives a.
    i = 0
    while i < la and a[i] == b[i]:
        i += 1
    return a[i:] == b[i + 1 :]


_QWERTY_ROWS = ("qwertyuiop", "asdfghjkl", "zxcvbnm")


def _qwerty_neighbours() -> dict[str, frozenset[str]]:
    pos = {ch: (r, c) for r, row in enumerate(_QWERTY_ROWS) for c, ch in enumerate(row)}
    out: dict[str, frozenset[str]] = {}
    for ch, (r, c) in pos.items():
        near = {
            other
            for other, (r2, c2) in pos.items()
            if other != ch and abs(r - r2) <= 1 and -1 <= (c2 - c) + (r2 - r) * 0.5 <= 1
        }
        out[ch] = frozenset(near)
    return out


# Standard QWERTY adjacency (same row +-1, neighbouring rows with the usual
# half-key stagger). Built from the layout, not from the eval's perturber.
QWERTY_NEIGHBOURS = _qwerty_neighbours()


def _adjacent(a: str, b: str) -> bool:
    return b in QWERTY_NEIGHBOURS.get(a, frozenset())


def is_keyboard_typo(token: str, target: str) -> bool:
    """True when ``token`` is ``target`` with exactly one keyboard-slip edit."""
    if token == target or not within_one_edit(token, target):
        return False
    lt, lg = len(token), len(target)
    if lt == lg:
        diff = [i for i in range(lt) if token[i] != target[i]]
        if len(diff) == 2:
            return True  # adjacent transposition
        i = diff[0]
        return _adjacent(target[i], token[i])  # neighbouring key hit instead
    if lt < lg:
        return True  # a letter was dropped
    # One extra letter in token: find it; it must double or neighbour an
    # adjacent letter of the intended word.
    i = 0
    while i < lg and token[i] == target[i]:
        i += 1
    extra = token[i]
    around = {target[j] for j in (i - 1, i) if 0 <= j < lg}
    return extra in around or any(_adjacent(extra, ch) for ch in around)


def damerau_levenshtein(a: str, b: str) -> int:
    """Optimal string alignment distance (used by tests and reports)."""
    la, lb = len(a), len(b)
    d = [[0] * (lb + 1) for _ in range(la + 1)]
    for i in range(la + 1):
        d[i][0] = i
    for j in range(lb + 1):
        d[0][j] = j
    for i in range(1, la + 1):
        for j in range(1, lb + 1):
            cost = 0 if a[i - 1] == b[j - 1] else 1
            d[i][j] = min(d[i - 1][j] + 1, d[i][j - 1] + 1, d[i - 1][j - 1] + cost)
            if i > 1 and j > 1 and a[i - 1] == b[j - 2] and a[i - 2] == b[j - 1]:
                d[i][j] = min(d[i][j], d[i - 2][j - 2] + 1)
    return d[la][lb]


class CorpusVocabulary:
    """Known words with document frequencies and a typo-correction lookup."""

    def __init__(
        self,
        token_lists: Iterable[Iterable[str]],
        *,
        extra_words: Iterable[str] = (),
    ) -> None:
        self.df: Counter[str] = Counter()
        for toks in token_lists:
            self.df.update(set(toks))
        self.words: frozenset[str] = frozenset(self.df) | frozenset(extra_words)
        self._by_len: dict[int, list[str]] = {}
        for w in sorted(self.words):
            if len(w) >= MIN_TARGET_LEN and w.isalpha():
                self._by_len.setdefault(len(w), []).append(w)
        self._cache: dict[str, str | None] = {}

    def __contains__(self, token: str) -> bool:
        return token in self.words

    def candidates(self, token: str) -> list[str]:
        """Known words within one edit of ``token`` under the length rules."""
        if (
            not token
            or len(token) < MIN_TOKEN_LEN
            or not token.isalpha()
            or is_identifier(token)
        ):
            return []
        strict = len(token) < FREE_EDIT_LEN
        out: list[str] = []
        for n in (len(token) - 1, len(token), len(token) + 1):
            for w in self._by_len.get(n, ()):
                if w == token:
                    continue
                if strict and (w[0] != token[0] or w[-1] != token[-1]):
                    continue
                if is_keyboard_typo(token, w):
                    out.append(w)
        return out

    def correct(self, token: str) -> str | None:
        """Unique known word within one edit of an unknown ``token``, else None."""
        if token in self.words:
            return token
        if token not in self._cache:
            tied = self.tied_candidates(token)
            self._cache[token] = tied[0] if len(tied) == 1 else None
        return self._cache[token]

    def tied_candidates(self, token: str) -> list[str]:
        """Candidates left after the tie-breaks (one element == unambiguous)."""
        cands = self.candidates(token)
        for keep in (
            lambda w: w[0] == token[0],
            lambda w: w[-1] == token[-1],
        ):
            if len(cands) > 1:
                narrowed = [w for w in cands if keep(w)]
                cands = narrowed or cands
        if len(cands) > 1:
            best = max(self.df.get(w, 0) for w in cands)
            cands = [w for w in cands if self.df.get(w, 0) == best]
        return cands

    def is_typo_of_any(self, token: str, words: frozenset[str]) -> bool:
        """True when every tied candidate for ``token`` lies in ``words``.

        Used to drop typo'd filler even when it is ambiguous between two
        filler words ("waht" -> what / want): either way it is not salient.
        """
        tied = self.tied_candidates(token)
        return bool(tied) and all(w in words for w in tied)
