"""Diceware-style passphrases typed right after a credential noun, with no copula.

``explain_redact.DISCLOSED_SECRET_RE`` needs a copula or ":" / "=" after the
credential noun ("the vault passphrase is ..."). People also write "the deploy
token marble-meadow-lagoon-badger stopped working" or "log in with passphrase
Lagoon Mosaic Velvet Sonnet 83 please": the value follows the noun directly.
Those words have no shape, and the character model finds them plausible
English, so neither the shape patterns nor ``secret_entropy`` sees them.

Rule (offline, no eval text):

1. A credential noun (the same cue list as the disclosure pattern), then a run
   of up to ``MAX_WORDS`` plain alphabetic words joined by spaces or by one
   consistent ``-`` / ``.`` / ``_``, optionally ending in a 1-4 digit number.
   A space-separated run stops at a stopword (``text.STOPWORDS`` plus clause
   and preposition words) or a credential-state word ("the token is expired"
   never starts a run).
2. Words are *ops words* when they are in the ops-domain vector vocabulary
   (6,000 frequent words of the Stack Exchange snapshot,
   ``domain_vectors``) or in the corpus vocabulary. Trailing ops words are
   trimmed from a space-separated run ("... badger stopped working" keeps
   "stopped working").
3. The run is a passphrase when it keeps at least ``MIN_WORDS`` words and at
   least ``max(2, ceil(n / 2))`` of them are not ops words. A separator-joined
   compound is redacted whole or not at all, so service names made of ops
   words ("payments-api-canary-pool") stay.

Known gap until Oct 29: a passphrase built mostly from ops words ("juniper orbit
copper tundra" -> three of four are in the vector vocabulary) leaked. The
incoherence arm closes it for space-joined runs of four or more words; an
ops-word compound joined by ``-`` / ``.`` / ``_`` still leaks.

Two knobs (Oct 29; ``passphrase_wordlist`` measures them on real EFF diceware
passphrases). The shipped detector uses ``tail="keep"`` and the incoherence arm at
0.10 on space-joined runs only (``DEFAULT_*`` below), after a pre-registered
calibration, a failed-on-identifiers first confirm and an amended one-shot confirm
(``passphrase_tail_protocol``): leaked words 105 -> 76 of 5,886 on the
fresh seed, 0 new Stack Exchange test flags, 0 new identifier flags. The
Oct 13 behaviour is ``tail="trim", coherence_max=None``:

* ``tail="keep"``: once a space-joined run is a passphrase, redact it up to the
  run's end (the stop word, or ``MAX_WORDS``) instead of trimming trailing ops
  words. The *decision* still uses the trimmed run, so the set of flagged
  sentences is unchanged; only the span grows. It trades over-redacting words
  like "stopped working" for not leaking a passphrase's last word when that word
  happens to be an ops word ("... uplifted component").
* ``coherence_max=c``: a run of at least ``COHERENCE_MIN_WORDS`` words that fails
  the ops-word count is still a passphrase when its words are mutually unrelated:
  the mean pairwise cosine of the ops-domain vectors (a pair with a word missing
  from the table counts 0) is below ``c``. Diceware draws words independently, so
  their pairs look unrelated; prose after a credential noun ("management tool like
  HashiCorp Vault") tends to stay on one topic. The vectors are 48-d, so the
  separation is weak and ``c`` needs a false-positive budget.
  ``coherence_compounds=False`` applies the arm to space-joined runs only: on
  ``-`` / ``.`` / ``_`` compounds it also fires on multi-part identifiers of the
  repo's own data ("sidecar-mesh-mtls-handshake-budget"), which the first
  protocol did not check (found after its confirm; see the amendment in
  ``passphrase_tail_protocol``).
"""

from __future__ import annotations

import json
import math
import re
from functools import lru_cache
from pathlib import Path
from typing import Callable, Iterator

from ops_copilot.secret_entropy import _Match
from ops_copilot.text import STOPWORDS

CORPUS_DIR = Path(__file__).resolve().parents[2] / "data" / "corpus"
MAX_WORDS = 6
MIN_WORDS = 3
COHERENCE_MIN_WORDS = 4
TAIL_MODES = ("trim", "keep")
DEFAULT_TAIL = "keep"
DEFAULT_COHERENCE_MAX: float | None = 0.10
DEFAULT_COHERENCE_COMPOUNDS = False
DEFAULT_EXEMPT_IDENTIFIERS = False
DATA_DIR = CORPUS_DIR.parent
_IDENT_SUFFIXES = (".jsonl", ".json", ".yaml", ".yml", ".md", ".txt")
_IDENT_RE = re.compile(r"(?<![\w-])[a-z]{3,12}(?:([-._])[a-z]{3,12})(?:\1[a-z]{3,12}){1,4}(?![\w-])")

_CUE = (
    r"pass(?:word|phrase|code)s?|passwd|pin|secret|token|credentials?|"
    r"api[ _-]?key|access[ _-]?key|private[ _-]?key"
)
_WORD = r"[A-Za-z]{3,12}"
_NUM = r"\d{1,4}"
CUED_RE = re.compile(
    rf"(?i)\b(?:{_CUE})\s+"
    rf"(?P<val>{_WORD}(?P<sep>[-._]){_WORD}(?:(?P=sep){_WORD}){{1,{MAX_WORDS - 2}}}(?:(?P=sep){_NUM})?"
    rf"|{_WORD}(?:\s+{_WORD}){{1,{MAX_WORDS - 1}}}(?:\s+{_NUM})?)"
    rf"(?![\w-])"
)
_SPACE_STOP = frozenset(
    "is was are were be been and but so or why what how who when where can could would please does do did then "
    "to for with from in on at of by via into the a an my our your their this that it its not no never "
    "expired expiring invalid valid revoked rotated missing wrong incorrect empty blank required leaked "
    "compromised correct stale old new outdated disabled enabled locked unlocked broken unset changed reset "
    "null none ok okay fine bad weak strong rejected accepted denied deleted lost forgotten wiped".split()
) | STOPWORDS


@lru_cache(maxsize=1)
def corpus_vocabulary() -> frozenset[str]:
    words: set[str] = set()
    for path in sorted(CORPUS_DIR.glob("*.jsonl")):
        for ln in path.read_text(encoding="utf-8").splitlines():
            if ln.strip():
                d = json.loads(ln)
                text = f"{d.get('doc_id', '')} {d.get('title', '')} {d.get('body', '')}".lower()
                words.update(re.findall(r"[a-z]+", text))
    return frozenset(words)


@lru_cache(maxsize=1)
def known_identifiers() -> frozenset[str]:
    """Lower-case 3-6 part ``-`` / ``.`` / ``_`` names in the repo's own ``data/`` text files.

    These are the service, doc, dashboard and flag names the copilot already knows
    ("sidecar-mesh-mtls-handshake-budget", "cache.flush.orchestrator"). With
    ``exempt_identifiers=True`` a compound equal to one of them (case-insensitive) is
    never a passphrase. It is an *exact* list: a new service that is not yet in
    ``data/`` gets no protection from it, which is what the Stack Exchange identifier
    set in ``passphrase_identifiers`` measures. Gzipped and binary files are skipped,
    so the EFF wordlist itself never enters the list.
    """
    found: set[str] = set()
    for path in sorted(DATA_DIR.rglob("*")):
        if path.is_file() and path.suffix in _IDENT_SUFFIXES:
            text = path.read_text(encoding="utf-8", errors="ignore").lower()
            found.update(m.group() for m in _IDENT_RE.finditer(text))
    return frozenset(found)


@lru_cache(maxsize=1)
def ops_vocabulary() -> frozenset[str]:
    from ops_copilot.domain_vectors import default_vectors

    return frozenset(default_vectors().index) | corpus_vocabulary()


def mean_pair_cosine(words: list[str], vectors=None) -> float:
    """Mean cosine over all word pairs (lower-cased); a pair with an unknown word counts 0."""
    import itertools

    if vectors is None:
        from ops_copilot.domain_vectors import default_vectors

        vectors = default_vectors()
    ws = [w.lower() for w in words]
    pairs = list(itertools.combinations(ws, 2))
    if not pairs:
        return 0.0
    tot = 0.0
    for a, b in pairs:
        s = vectors.similarity(a, b)
        tot += 0.0 if s is None else s
    return tot / len(pairs)


def _enough(words: list[str], is_ops: Callable[[str], bool]) -> bool:
    if len(words) < MIN_WORDS:
        return False
    plain = sum(not is_ops(w.lower()) for w in words)
    return plain >= max(2, math.ceil(len(words) / 2))


class CuedPassphraseDetector:
    """Regex-like (``finditer`` / ``subn`` / ``search``); the match is the value only."""

    pattern = "<cued diceware passphrase detector>"

    def __init__(
        self,
        vocabulary: frozenset[str] | None = None,
        *,
        tail: str = DEFAULT_TAIL,
        coherence_max: float | None = DEFAULT_COHERENCE_MAX,
        coherence_compounds: bool = DEFAULT_COHERENCE_COMPOUNDS,
        exempt_identifiers: bool = DEFAULT_EXEMPT_IDENTIFIERS,
        vectors=None,
    ):
        if tail not in TAIL_MODES:
            raise ValueError(f"tail must be one of {TAIL_MODES}")
        self._vocab = vocabulary
        self.tail = tail
        self.coherence_max = coherence_max
        self.coherence_compounds = coherence_compounds
        self.exempt_identifiers = exempt_identifiers
        self._vectors = vectors

    def _incoherent(self, words: list[str]) -> bool:
        if self.coherence_max is None or len(words) < COHERENCE_MIN_WORDS:
            return False
        return mean_pair_cosine(words, self._vectors) < self.coherence_max

    @staticmethod
    def _is_known_identifier(val: str, sep: str) -> bool:
        """The compound, or the compound without a trailing number part, is a ``data/`` name."""
        low = val.lower()
        parts = low.split(sep)
        bare = sep.join(parts[:-1]) if parts and parts[-1].isdigit() else low
        ids = known_identifiers()
        return low in ids or bare in ids

    @property
    def vocabulary(self) -> frozenset[str]:
        return self._vocab if self._vocab is not None else ops_vocabulary()

    def _span(self, m: re.Match[str]) -> tuple[int, int] | None:
        vocab = self.vocabulary
        is_ops = vocab.__contains__
        a, b = m.span("val")
        val = m.group("val")
        if m.group("sep"):
            if self.exempt_identifiers and self._is_known_identifier(val, m.group("sep")):
                return None
            words = [w for w in val.split(m.group("sep")) if w.isalpha()]
            if _enough(words, is_ops):
                return (a, b)
            return (a, b) if self.coherence_compounds and self._incoherent(words) else None
        toks = list(re.finditer(r"\S+", val))
        keep: list[re.Match[str]] = []
        for t in toks:
            if t.group().lower() in _SPACE_STOP:
                break
            keep.append(t)
        words = [t for t in keep if t.group().isalpha()]
        full = list(words)
        while words and is_ops(words[-1].group().lower()):
            words.pop()
        if not _enough([t.group() for t in words], is_ops):
            if not self._incoherent([t.group() for t in full]):
                return None
            words = full
        if self.tail == "keep":
            words = full
        last = keep.index(words[-1])
        nxt = keep[last + 1] if last + 1 < len(keep) else None
        end = nxt.end() if nxt is not None and nxt.group().isdigit() else words[-1].end()
        return (a + words[0].start(), a + end)

    def finditer(self, text: str) -> Iterator[_Match]:
        for m in CUED_RE.finditer(text or ""):
            sp = self._span(m)
            if sp is not None:
                yield _Match(text, sp)

    def search(self, text: str) -> _Match | None:
        return next(self.finditer(text), None)

    def subn(self, repl, text: str) -> tuple[str, int]:
        out, last, n = [], 0, 0
        for m in self.finditer(text or ""):
            a, b = m.span()
            out.append(text[last:a])
            out.append(repl(m) if callable(repl) else repl)
            last, n = b, n + 1
        out.append((text or "")[last:])
        return "".join(out), n

    def sub(self, repl, text: str) -> str:
        return self.subn(repl, text)[0]


CUED_PASSPHRASE = CuedPassphraseDetector()
