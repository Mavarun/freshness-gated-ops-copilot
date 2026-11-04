"""Passphrases drawn from a real diceware wordlist, and how many of their words leak.

The Oct 13 probe (``explain_eval`` section 7) used 32 hand-picked words that were
chosen to be *absent* from the ops vocabulary, so it could not see the detector's
documented gap: a passphrase made of words the ops vocabulary knows. Real
passphrase generators do not avoid ops words. The EFF large wordlist (7,776
words, ``data/passphrase``) shares 1,342 words with the ops vocabulary (17%),
so a 5-word EFF passphrase has three or more ops words about 4% of the time and
at least one ops word 61% of the time.

``wordlist_passphrases(seed, n)`` draws ``n`` rows: 4-6 distinct alphabetic EFF
words, a separator from {space, -, ., _}, half Title-Case with a trailing
two-digit number (as in the Oct 13 probe), placed in one of the five Oct 13
templates. ``score_rows`` runs the trace ``query`` redaction (the boundary pass,
fragment pass included) with a given pattern set and counts:

* ``leak_rows`` / ``leak_words``: rows with any passphrase word (4+ letters) left
  in the redacted query, and how many such words;
* ``over_words``: template words (4+ letters, not in the passphrase) that were
  redacted, the price of a wider span;
* ``cause``: a post-hoc label for every leaking row (``no_flag_ops`` when the
  run had too few non-ops words, ``stop_inside`` when a passphrase word is in the
  run stop list, ``tail_trim`` when only trailing words leaked, ``other``).
"""

from __future__ import annotations

import gzip
import random
import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any, Sequence

DATA = Path(__file__).resolve().parents[2] / "data" / "passphrase" / "eff_large_wordlist.txt.gz"
WORDLIST_SHA256 = "addd35536511597a02fa0a9ff1e5284677b8883b83e986e43f15a3db996b903e"
SEPARATORS = (" ", "-", ".", "_")
SEP_NAMES = {" ": "space", "-": "hyphen", ".": "dot", "_": "underscore"}
LENGTHS = (4, 5, 6)


@lru_cache(maxsize=1)
def eff_words() -> tuple[str, ...]:
    """The 7,772 purely alphabetic words of the EFF large list (4 hyphenated ones dropped)."""
    import hashlib

    raw = gzip.decompress(DATA.read_bytes())
    if hashlib.sha256(raw).hexdigest() != WORDLIST_SHA256:
        raise ValueError("EFF wordlist does not match the pinned sha256")
    out = []
    for ln in raw.decode("utf-8").splitlines():
        parts = ln.split("\t")
        if len(parts) == 2 and parts[1].isalpha():
            out.append(parts[1])
    return tuple(out)


@dataclass(frozen=True)
class ProbeRow:
    secret: str
    words: tuple[str, ...]
    separator: str
    context: str
    template: str

    @property
    def text(self) -> str:
        return self.template.format(s=self.secret)


def _templates() -> list[tuple[str, str]]:
    from ops_copilot.explain_eval import PASSPHRASE_TEMPLATES

    return [(ctx, t) for ctx, ts in PASSPHRASE_TEMPLATES.items() for t in ts]


WORDNET_NOUNS = Path(__file__).resolve().parents[2] / "data" / "wordnet" / "wn_noun_neighbours.json.gz"


@lru_cache(maxsize=1)
def offlist_words() -> tuple[str, ...]:
    """Control word source: 4-9 letter lower-case WordNet nouns that are *not* on the EFF list.

    Taken from the keys of the committed WordNet neighbour table (``data/wordnet``),
    so it is offline and pinned by that file. A passphrase built from these words is
    what a generator with a different list (or a person) would type; an arm that
    keys on EFF membership should gain nothing on it, which is the point of the
    control.
    """
    import json

    keys = json.loads(gzip.decompress(WORDNET_NOUNS.read_bytes()))["neighbours"]
    eff = set(eff_words())
    return tuple(sorted(w for w in keys if w.isalpha() and w.islower() and 4 <= len(w) <= 9 and w not in eff))


NUMBER_STYLES = ("token", "attached")


def wordlist_passphrases(
    seed: int, n: int, *, words: Sequence[str] | None = None, number_style: str = "token"
) -> list[ProbeRow]:
    """``n`` seeded probe rows; ``words`` swaps the word source (default: the EFF list).

    ``number_style="token"`` (the Oct 29 rows): half the rows are Title-Case with a
    trailing two-digit number as its own part. ``"attached"`` is how Bitwarden's
    generator does it (``appendRandomNumberToRandomWord``): every row carries one
    digit 0-9 glued to a random word ("Ranch3"), and half are Title-Case.
    """
    if number_style not in NUMBER_STYLES:
        raise ValueError(f"number_style must be one of {NUMBER_STYLES}")
    if number_style == "attached":
        return _attached_rows(seed, n, eff_words() if words is None else tuple(words))
    rng = random.Random(seed)
    words = eff_words() if words is None else tuple(words)
    tpls = _templates()
    rows: list[ProbeRow] = []
    for i in range(n):
        ws = rng.sample(words, rng.choice(LENGTHS))
        sep = SEPARATORS[i % len(SEPARATORS)]
        ctx, tpl = tpls[rng.randrange(len(tpls))]
        parts = list(ws)
        if rng.random() < 0.5:
            parts = [w.title() for w in parts] + [str(rng.randint(10, 99))]
        rows.append(ProbeRow(sep.join(parts), tuple(ws), SEP_NAMES[sep], ctx, tpl))
    return rows


def _attached_rows(seed: int, n: int, words: tuple[str, ...]) -> list[ProbeRow]:
    rng = random.Random(seed)
    tpls = _templates()
    rows: list[ProbeRow] = []
    for i in range(n):
        ws = rng.sample(words, rng.choice(LENGTHS))
        sep = SEPARATORS[i % len(SEPARATORS)]
        ctx, tpl = tpls[rng.randrange(len(tpls))]
        parts = [w.title() for w in ws] if rng.random() < 0.5 else list(ws)
        k = rng.randrange(len(parts))
        parts[k] = parts[k] + str(rng.randint(0, 9))
        rows.append(ProbeRow(sep.join(parts), tuple(ws), SEP_NAMES[sep], ctx, tpl))
    return rows


def _present(blob: str, word: str) -> bool:
    return re.search(rf"(?<![a-z]){re.escape(word)}(?![a-z])", blob) is not None


def redact_query(text: str, patterns) -> str:
    from ops_copilot.explain_redact import redact_boundary

    out, _ = redact_boundary({"query": text}, query=text, patterns=patterns)
    return str(out["query"])


def _cause(row: ProbeRow, leaked: list[str]) -> str:
    from ops_copilot.passphrase import _SPACE_STOP, ops_vocabulary

    ws = [w.lower() for w in row.words]
    if row.separator == "space" and any(w in _SPACE_STOP for w in ws):
        return "stop_inside"
    if len(leaked) == len([w for w in ws if len(w) >= 4]):
        ops = ops_vocabulary()
        return "no_flag_ops" if sum(w not in ops for w in ws) < max(2, -(-len(ws) // 2)) else "other"
    tail = [w for w in ws if len(w) >= 4][-len(leaked):]
    return "tail_trim" if leaked == tail else "other"


def score_rows(rows: Sequence[ProbeRow], patterns) -> dict[str, Any]:
    tot = {"rows": 0, "words": 0, "leak_rows": 0, "leak_words": 0, "over_words": 0}
    by_sep: dict[str, dict[str, int]] = {}
    cause: dict[str, int] = {}
    examples: list[dict[str, Any]] = []
    for r in rows:
        red = redact_query(r.text, patterns).lower()
        words = [w.lower() for w in r.words if len(w) >= 4]
        leaked = [w for w in words if _present(red, w)]
        tpl_words = [w for w in re.findall(r"[a-z]{4,}", r.template.lower()) if w not in words]
        over = sum(not _present(red, w) for w in dict.fromkeys(tpl_words))
        s = by_sep.setdefault(r.separator, {"rows": 0, "leak_rows": 0, "leak_words": 0})
        s["rows"] += 1
        tot["rows"] += 1
        tot["words"] += len(words)
        tot["over_words"] += over
        if leaked:
            c = _cause(r, leaked)
            cause[c] = cause.get(c, 0) + 1
            s["leak_rows"] += 1
            s["leak_words"] += len(leaked)
            tot["leak_rows"] += 1
            tot["leak_words"] += len(leaked)
            if len(examples) < 8:
                examples.append({"text": r.text, "leaked": leaked, "cause": c})
    return {"total": tot, "by_separator": by_sep, "cause": dict(sorted(cause.items())), "examples": examples}


# ---------------------------------------------------------------------------
# Oct 31: passphrases made of invented words (the cost control of ``plain_rule``)

INVENTED_POOL_SEED = 7331
INVENTED_POOL_SIZE = 4000
INVENTED_SHAPES = ("cv", "cvc")
_ONSETS = "bcdfghjklmnprstvwz"
_VOWEL_SET = "aeiou"


def _invented_word(rng: random.Random, shape: str) -> str:
    if shape == "cv":  # strict consonant-vowel alternation, 2-4 syllables ("bafiku")
        return "".join(rng.choice(_ONSETS) + rng.choice(_VOWEL_SET) for _ in range(rng.randint(2, 4)))
    # closed syllables, 2 of them ("zorbak", "quintel"-like): never strictly CV
    return "".join(rng.choice(_ONSETS) + rng.choice(_VOWEL_SET) + rng.choice(_ONSETS) for _ in range(2))


@lru_cache(maxsize=4)
def invented_words(shape: str) -> tuple[str, ...]:
    """A fixed pool of invented words of one shape, none in the dictionary or the ops vocabulary.

    People and pronounceable generators type passphrases from words that are in no
    list. ``plain_rule="dict"`` would stop counting them, so this pool measures what
    that costs. ``cv`` words are what ``plain_rule="dict_cv"`` lets back in; ``cvc``
    words are not, so neither rule is graded on a pool built for it alone.
    """
    from ops_copilot.passphrase import in_dictionary, ops_vocabulary

    if shape not in INVENTED_SHAPES:
        raise ValueError(f"shape must be one of {INVENTED_SHAPES}")
    rng = random.Random(f"{INVENTED_POOL_SEED}-{shape}")
    ops = ops_vocabulary()
    out: dict[str, None] = {}
    while len(out) < INVENTED_POOL_SIZE:
        w = _invented_word(rng, shape)
        if w not in ops and not in_dictionary(w):
            out[w] = None
    return tuple(out)


def invented_passphrases(seed: int, n: int) -> list[ProbeRow]:
    """``n`` probe rows in the Oct 29 shape; even rows draw ``cv`` words, odd rows ``cvc``."""
    half = (n + 1) // 2
    cv = wordlist_passphrases(seed, half, words=invented_words("cv"))
    cvc = wordlist_passphrases(seed + 1, n - half, words=invented_words("cvc"))
    out: list[ProbeRow] = []
    for i in range(n):
        out.append(cv[i // 2] if i % 2 == 0 else cvc[i // 2])
    return out


# ---------------------------------------------------------------------------
# Nov 1: cost controls for ``shape_guards`` (case-styled and phrase passphrases)

CASE_STYLES = ("upper", "alternate", "random", "invert")
PHRASE_WORDS = ("and", "the", "of", "with", "for", "to", "in", "on", "my", "you", "is", "at", "by", "or")


def _case(word: str, style: str, rng: random.Random, i: int) -> str:
    if style == "upper":  # KeePassXC "UPPER CASE"
        return word.upper()
    if style == "alternate":  # xkpasswd ALTERNATE: lower / UPPER word by word
        return word.upper() if i % 2 else word.lower()
    if style == "invert":  # xkpasswd INVERT: cASCADE
        return word[:1].lower() + word[1:].upper()
    return rng.choice((word.lower(), word.upper(), word.title()))  # xkpasswd RANDOM (per word)


def cased_passphrases(seed: int, n: int) -> list[ProbeRow]:
    """``n`` EFF passphrases in the case styles other generators emit.

    Rows cycle through UPPER (KeePassXC), word-alternating lower / UPPER, per-word
    random lower / UPPER / Title, and inverted (``cASCADE``, xkpasswd); separators
    cycle as in ``wordlist_passphrases``, and every other row has a trailing
    two-digit number. The ``case`` shape guard must never fire on these.
    """
    rng = random.Random(seed)
    words = eff_words()
    tpls = _templates()
    rows: list[ProbeRow] = []
    for i in range(n):
        ws = rng.sample(words, rng.choice(LENGTHS))
        sep = SEPARATORS[i % len(SEPARATORS)]
        style = CASE_STYLES[(i // len(SEPARATORS)) % len(CASE_STYLES)]
        ctx, tpl = tpls[rng.randrange(len(tpls))]
        parts = [_case(w, style, rng, j) for j, w in enumerate(ws)]
        if rng.random() < 0.5:
            parts.append(str(rng.randint(10, 99)))
        rows.append(ProbeRow(sep.join(parts), tuple(ws), SEP_NAMES[sep], ctx, tpl))
    return rows


def phrase_passphrases(seed: int, n: int, *, words: Sequence[str] | None = None) -> list[ProbeRow]:
    """``n`` rows of 3-5 EFF words with one short function word inside (``ocean-and-velvet-badger``).

    A person who types a phrase as a passphrase writes connectives; the ``stop``
    shape guard reads such a compound as prose. Only the EFF words count as secret
    words when scoring (``words``), so a leak means a real passphrase word was left.
    The function word is drawn from ``PHRASE_WORDS`` and placed at a random inner
    position; separators cycle through ``-``, ``.``, ``_`` and space.
    """
    rng = random.Random(seed)
    words = eff_words() if words is None else tuple(words)
    tpls = _templates()
    rows: list[ProbeRow] = []
    for i in range(n):
        ws = rng.sample(words, rng.choice((3, 4, 5)))
        sep = SEPARATORS[i % len(SEPARATORS)]
        ctx, tpl = tpls[rng.randrange(len(tpls))]
        parts = list(ws)
        parts.insert(rng.randint(1, len(parts) - 1), rng.choice(PHRASE_WORDS))
        if rng.random() < 0.5:
            parts = [p.title() for p in parts]
        rows.append(ProbeRow(sep.join(parts), tuple(ws), SEP_NAMES[sep], ctx, tpl))
    return rows


# ---------------------------------------------------------------------------
# Nov 4: a held-out-connective control for ``space_bridge`` (reported, not gating)

CONNECTIVE_WORDS = (
    "because", "without", "between", "while", "after", "before", "through",
    "against", "within", "across", "since", "though", "whether", "per",
)


def connective_passphrases(seed: int, n: int) -> list[ProbeRow]:
    """``phrase_passphrases`` with connectives that are on no bridge list and not on the EFF list.

    The phrase probe draws its function words from ``PHRASE_WORDS``, and every one of them is on
    ``passphrase.FUNCTION_WORDS``, so it overstates what a function-word list can do on real
    phrases. These 14 words (``because``, ``without``...) are on none of the lists
    (``passphrase.bridge_words``) and not on the EFF list, so a gain here would have to come from a
    reading that generalises past a list. Rows are otherwise built like the phrase rows: 3-5 EFF
    words, one inner connective, half Title-Case, separators cycling through ``-``, ``.``, ``_`` and space.
    """
    rng = random.Random(seed)
    words = eff_words()
    tpls = _templates()
    rows: list[ProbeRow] = []
    for i in range(n):
        ws = rng.sample(words, rng.choice((3, 4, 5)))
        sep = SEPARATORS[i % len(SEPARATORS)]
        ctx, tpl = tpls[rng.randrange(len(tpls))]
        parts = list(ws)
        parts.insert(rng.randint(1, len(parts) - 1), rng.choice(CONNECTIVE_WORDS))
        if rng.random() < 0.5:
            parts = [p.title() for p in parts]
        rows.append(ProbeRow(sep.join(parts), tuple(ws), SEP_NAMES[sep], ctx, tpl))
    return rows


def offlist_phrase_passphrases(seed: int, n: int) -> list[ProbeRow]:
    """``phrase_passphrases`` over the off-list control words (``offlist_words``) instead of the EFF list.

    A passphrase a person or another generator writes from words outside the EFF list. A reading that
    keys on EFF membership (``space_bridge_rule="eff3"``) should gain nothing here, which is the point.
    """
    return phrase_passphrases(seed, n, words=offlist_words())
