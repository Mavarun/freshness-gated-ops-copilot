"""Random-looking tokens with no recognisable format (entropy-based secret detection).

The pattern pass in ``explain_redact`` knows the *shapes* of secrets: AWS key
ids, Slack tokens, ``key=value`` assignments, and strings of 32+ characters
mixing letters and digits. A 12-31 character random string with no prefix
(``q7xf2lpz9mkw3t``, ``9f3c1ab07e4d2c88``, ``ZmFrZS1rZXktMDE``) matches none of
them, so a user who pastes a personal access token or a generated password
without saying "token is" leaves it in the trace.

Model. A token is "random" when an English / ops-vocabulary character model is
surprised by it. A character trigram model (interpolated with bigram and
unigram, add-k smoothing; Jelinek-Mercer weights fixed below) is trained on
words that are already committed as outside data:

- the general-English words of the counter-fitted neighbour table
  (``data/wordvec``), the question-side words of the Stack Exchange QA table
  (``data/qa``), the Wiktionary computing headwords and glosses
  (``data/wiktionary``) and the Stack Exchange tag names (``data/tagsyn``,
  which carry real tool spellings such as ``postgresql-9.6`` or ``x86-64``).

The corpus documents and every eval file are **not** training data, so the
false-positive rate on them (``secret_entropy_eval``) is measured on text the
model never saw. The score is the cross-entropy of the lower-cased token in
bits per character (queries are lower-cased before parsing, so case carries no
signal here). Uniform random lower-case alphanumerics cost log2(36) = 5.17
bits per character under a uniform model and more under an English one;
English words and hyphenated identifiers cost about 2.5-3.5.

Which tokens are candidates: a whitespace-delimited run of at least
``MIN_LEN`` characters, edge punctuation stripped, with at least one letter,
no ``@`` (e-mail addresses have their own detector), no ``[`` / ``]`` (already
redacted) and no ``://`` (URLs). Each ``-_./`` separated piece of at least
``MIN_PIECE`` characters is scored on its own and the token is flagged if any
piece is over ``threshold``, so ``deploy-token-q7xf2lpz9mkw`` is caught by its
last piece while ``payments-worker-heartbeat`` is not.

The threshold is chosen by ``calibrate_threshold`` on a *calibration* split
only: seeded synthetic secrets of the "dev" families vs held-out vocabulary
words (a salted-hash split the character model is not trained on) and
identifier-style compounds of them. Rule (fixed before the test numbers were
looked at), a max-margin choice on the grid: ``lo`` is the lowest threshold
whose false-positive rate on the calibration negatives is at most
``MAX_CALIB_FPR``, ``hi`` the highest threshold that still catches every dev
secret, and the threshold is their midpoint (rounded down to the grid). It
leaves equal room for secrets that score lower than the dev families and for
words that score higher than the calibration words. ``DEFAULT_THRESHOLD`` is
that value, pinned by a test that re-runs the calibration.

The detector duck-types the two ``re.Pattern`` methods ``explain_redact`` uses
(``finditer`` and ``subn``) so it can sit in the same pattern list.
"""

from __future__ import annotations

import gzip
import hashlib
import json
import math
import random
import re
import string
from collections import Counter
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Callable, Iterable, Iterator, Sequence

DATA = Path(__file__).resolve().parents[2] / "data"
SOURCES = {
    "wordvec": DATA / "wordvec" / "cf_neighbours.json.gz",
    "qa": DATA / "qa" / "se_qa_translation.json.gz",
    "wiktionary": DATA / "wiktionary" / "computing_senses.json.gz",
    "tagsyn": DATA / "tagsyn" / "stackexchange_tag_synonyms.json.gz",
}
SPLIT_SALT = "secret-entropy-calibration"
CALIB_FRACTION = 0.15
MIN_LEN = 12
MIN_PIECE = 8
ADD_K = 0.05
LAMBDAS = (0.6, 0.3, 0.1)  # trigram, bigram, unigram
MAX_CALIB_FPR = 0.005
CALIBRATION_GRID = tuple(round(3.0 + 0.05 * i, 2) for i in range(81))  # 3.00 .. 7.00
DEFAULT_THRESHOLD = 4.85  # re-derived by tests/test_secret_entropy.py::test_default_threshold_is_calibrated
BOS, EOS = "^", "$"
_SEPARATORS = "-_./"
_ALPHABET = string.ascii_lowercase + string.digits + _SEPARATORS + "#"
_WORD_RE = re.compile(r"[a-z0-9][a-z0-9\-_.]*[a-z0-9]|[a-z]")
_RUN_RE = re.compile(r"\S+")
_EDGE = "\"'`()<>{},;:!?."
# ":" splits too, so timestamps (2026-09-13t12:00:00z) and host:port pairs
# fall apart into short pieces.
_PIECE_SPLIT = re.compile(r"[-_./:]+")


def _canon(ch: str) -> str:
    return ch if ch in _ALPHABET else "#"


def canon(token: str) -> str:
    """Lower-case, every character outside ``[a-z0-9-_./]`` folded to ``#``."""
    return "".join(_canon(c) for c in token.lower())


# ---------------------------------------------------------------------------
# training words


def _load(path: Path) -> dict:
    with gzip.open(path, "rt", encoding="utf-8") as fh:
        return json.load(fh)


def _words_of(text: str) -> list[str]:
    return _WORD_RE.findall(text.lower())


def source_words() -> dict[str, set[str]]:
    """Distinct lower-case words per vendored source (no corpus, no eval text)."""
    out: dict[str, set[str]] = {k: set() for k in SOURCES}
    wv = _load(SOURCES["wordvec"])
    out["wordvec"].update(w for w in wv["neighbours"] if _WORD_RE.fullmatch(w))
    qa = _load(SOURCES["qa"])
    for rows in qa["table"].values():
        out["qa"].update(r[0] for r in rows if _WORD_RE.fullmatch(r[0]))
    wk = _load(SOURCES["wiktionary"])
    for s in wk["senses"]:
        out["wiktionary"].update(_words_of(s.get("word", "")))
        out["wiktionary"].update(_words_of(s.get("gloss", "")))
        for syn in s.get("synonyms") or []:
            out["wiktionary"].update(_words_of(syn))
    ts = _load(SOURCES["tagsyn"])
    for p in ts["pairs"]:
        for t in (p["from_tag"], p["to_tag"]):
            t = t.strip(".")
            if t:
                out["tagsyn"].add(t.lower())
    return out


def _in_calib(word: str) -> bool:
    h = hashlib.sha256(f"{SPLIT_SALT}:{word}".encode()).digest()
    return int.from_bytes(h[:4], "big") / 2**32 < CALIB_FRACTION


def vocabulary_split() -> tuple[list[str], list[str]]:
    """(train words, calibration words): a salted-hash split of all source words."""
    words = sorted(set().union(*source_words().values()))
    calib = [w for w in words if _in_calib(w)]
    train = [w for w in words if not _in_calib(w)]
    return train, calib


# ---------------------------------------------------------------------------
# character model


@dataclass
class CharTrigramModel:
    """Interpolated character trigram model over ``_ALPHABET`` plus boundaries."""

    tri: Counter = field(default_factory=Counter)
    tri_ctx: Counter = field(default_factory=Counter)
    bi: Counter = field(default_factory=Counter)
    bi_ctx: Counter = field(default_factory=Counter)
    uni: Counter = field(default_factory=Counter)
    n_uni: int = 0
    n_words: int = 0

    @classmethod
    def train(cls, words: Iterable[str]) -> "CharTrigramModel":
        m = cls()
        for w in words:
            s = BOS + BOS + canon(w) + EOS
            m.n_words += 1
            for i in range(2, len(s)):
                a, b, c = s[i - 2], s[i - 1], s[i]
                m.tri[(a, b, c)] += 1
                m.tri_ctx[(a, b)] += 1
                m.bi[(b, c)] += 1
                m.bi_ctx[b] += 1
                m.uni[c] += 1
                m.n_uni += 1
        return m

    @property
    def vocab_size(self) -> int:
        return len(_ALPHABET) + 1  # + EOS

    def prob(self, a: str, b: str, c: str) -> float:
        v = self.vocab_size
        p3 = (self.tri[(a, b, c)] + ADD_K) / (self.tri_ctx[(a, b)] + ADD_K * v)
        p2 = (self.bi[(b, c)] + ADD_K) / (self.bi_ctx[b] + ADD_K * v)
        p1 = (self.uni[c] + ADD_K) / (self.n_uni + ADD_K * v)
        l3, l2, l1 = LAMBDAS
        return l3 * p3 + l2 * p2 + l1 * p1

    def bits_per_char(self, token: str) -> float:
        """Cross-entropy of ``token`` (EOS included) in bits per character."""
        s = BOS + BOS + canon(token) + EOS
        n = len(s) - 2
        if n <= 0:
            return 0.0
        total = 0.0
        for i in range(2, len(s)):
            total -= math.log2(self.prob(s[i - 2], s[i - 1], s[i]))
        return total / n


@lru_cache(maxsize=1)
def default_model() -> CharTrigramModel:
    train, _ = vocabulary_split()
    return CharTrigramModel.train(train)


# ---------------------------------------------------------------------------
# candidates and scoring


def _strip_span(text: str, start: int, end: int) -> tuple[int, int]:
    while start < end and text[start] in _EDGE:
        start += 1
    while end > start and text[end - 1] in _EDGE:
        end -= 1
    return start, end


def is_candidate(token: str) -> bool:
    if len(token) < MIN_LEN:
        return False
    if "@" in token or "[" in token or "]" in token or "://" in token:
        return False
    return any(c.isalpha() for c in token)


def pieces(token: str) -> list[str]:
    """``-_./`` separated pieces of at least ``MIN_PIECE`` chars (or the whole token)."""
    parts = [p for p in _PIECE_SPLIT.split(token) if len(p) >= MIN_PIECE]
    return parts or ([token] if not _PIECE_SPLIT.search(token) else [])


def token_score(token: str, model: CharTrigramModel | None = None) -> float:
    """Highest bits-per-char over the token's pieces (0.0 if it has none)."""
    m = model or default_model()
    return max((m.bits_per_char(p) for p in pieces(token)), default=0.0)


class _Match:
    __slots__ = ("_s", "_span")

    def __init__(self, s: str, span: tuple[int, int]):
        self._s, self._span = s, span

    def group(self, i: int = 0) -> str:
        if i != 0:
            raise IndexError(i)
        return self._s[self._span[0] : self._span[1]]

    def span(self) -> tuple[int, int]:
        return self._span

    def start(self) -> int:
        return self._span[0]

    def end(self) -> int:
        return self._span[1]


class RandomTokenDetector:
    """Regex-like detector: ``finditer`` / ``subn`` / ``search`` over random tokens."""

    pattern = "<random-token char-trigram detector>"

    def __init__(self, threshold: float = DEFAULT_THRESHOLD, model: CharTrigramModel | None = None):
        self.threshold = float(threshold)
        self._model = model

    @property
    def model(self) -> CharTrigramModel:
        return self._model or default_model()

    def is_random(self, token: str) -> bool:
        return is_candidate(token) and token_score(token, self.model) >= self.threshold

    def finditer(self, text: str) -> Iterator[_Match]:
        for m in _RUN_RE.finditer(text or ""):
            a, b = _strip_span(text, m.start(), m.end())
            if b > a and self.is_random(text[a:b]):
                yield _Match(text, (a, b))

    def search(self, text: str) -> _Match | None:
        return next(self.finditer(text), None)

    def subn(self, repl: str | Callable[[_Match], str], text: str) -> tuple[str, int]:
        out, last, n = [], 0, 0
        for m in self.finditer(text):
            a, b = m.span()
            out.append(text[last:a])
            out.append(repl(m) if callable(repl) else repl)
            last, n = b, n + 1
        out.append(text[last:])
        return "".join(out), n

    def sub(self, repl, text: str) -> str:
        return self.subn(repl, text)[0]


RANDOM_TOKEN = RandomTokenDetector()


# ---------------------------------------------------------------------------
# synthetic secrets (never real) and calibration


def _rand(rng: random.Random, alphabet: str, n: int) -> str:
    return "".join(rng.choice(alphabet) for _ in range(n))


B62 = string.ascii_letters + string.digits
HEX = "0123456789abcdef"
B64URL = B62 + "-_"
PW_SYMBOLS = B62 + "!#$%^&*~+="

# family -> generator(rng). "dev" families feed calibration; "test" families
# are only scored in the eval (the last one, pronounceable strings, is a known
# hard case).
SECRET_FAMILIES: dict[str, Callable[[random.Random], str]] = {
    "base62": lambda r: _rand(r, B62, r.randint(12, 31)),
    "hex": lambda r: _rand(r, HEX, r.randint(16, 31)),
    "lower_alnum": lambda r: _rand(r, string.ascii_lowercase + string.digits, r.randint(12, 24)),
    "base64url": lambda r: _rand(r, B64URL, r.randint(16, 31)),
    "password_symbols": lambda r: _rand(r, PW_SYMBOLS, r.randint(12, 20)),
    "prefixed_pat": lambda r: r.choice(("deploy-key-", "svc_", "tok.")) + _rand(r, B62, r.randint(12, 24)),
    "pronounceable": lambda r: "".join(
        r.choice("bcdfghjklmnprstvz") + r.choice("aeiou") for _ in range(r.randint(6, 10))
    ),
}
DEV_FAMILIES = ("base62", "hex", "lower_alnum")
TEST_FAMILIES = tuple(SECRET_FAMILIES)


def synthetic_secrets(families: Sequence[str], n_per_family: int, seed: int) -> list[tuple[str, str]]:
    rng = random.Random(seed)
    out: list[tuple[str, str]] = []
    for fam in families:
        gen = SECRET_FAMILIES[fam]
        for _ in range(n_per_family):
            s = gen(rng)
            while not any(c.isalpha() for c in s):
                s = gen(rng)
            out.append((fam, s))
    return out


def compound_identifiers(words: Sequence[str], n: int, seed: int) -> list[str]:
    """Identifier-style joins of 2-4 words with ``-`` / ``_`` / ``.`` and optional digits."""
    rng = random.Random(seed)
    pool = [w for w in words if w.isalpha() and 3 <= len(w) <= 12]
    out: list[str] = []
    while len(out) < n:
        k = rng.randint(2, 4)
        sep = rng.choice("-_.")
        parts = [rng.choice(pool) for _ in range(k)]
        if rng.random() < 0.3:
            parts.append(str(rng.randint(1, 9999)))
        tok = sep.join(parts)
        if len(tok) >= MIN_LEN:
            out.append(tok)
    return out


def calibration_negatives(seed: int = 7, n_compounds: int = 2000) -> list[str]:
    _, calib = vocabulary_split()
    long_words = [w for w in calib if is_candidate(w)]
    return long_words + compound_identifiers(calib, n_compounds, seed)


def calibrate_threshold(
    model: CharTrigramModel | None = None,
    *,
    seed: int = 7,
    grid: Sequence[float] | None = None,
) -> dict:
    """Max-margin threshold between calibration FPR <= ``MAX_CALIB_FPR`` and dev TPR = 1."""
    m = model or default_model()
    neg = [token_score(t, m) for t in calibration_negatives(seed)]
    pos = [token_score(s, m) for _, s in synthetic_secrets(DEV_FAMILIES, 300, seed)]
    grid = list(grid or CALIBRATION_GRID)
    rows = []
    for t in grid:
        fpr = sum(s >= t for s in neg) / len(neg)
        tpr = sum(s >= t for s in pos) / len(pos)
        rows.append({"threshold": t, "calib_fpr": round(fpr, 4), "dev_tpr": round(tpr, 4)})
    lo = next((r["threshold"] for r in rows if r["calib_fpr"] <= MAX_CALIB_FPR), None)
    hi = max((r["threshold"] for r in rows if r["dev_tpr"] >= 1.0), default=None)
    if lo is None or hi is None or hi < lo:
        chosen = lo
    else:
        mid = (lo + hi) / 2
        chosen = max(t for t in grid if t <= mid + 1e-9)
    return {
        "threshold": chosen,
        "lo": lo,
        "hi": hi,
        "n_negatives": len(neg),
        "n_positives": len(pos),
        "grid": rows,
    }
