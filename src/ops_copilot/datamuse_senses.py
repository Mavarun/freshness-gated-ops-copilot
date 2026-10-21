"""Datamuse "means like" backoff: a usage-synonymy source for ops rewording.

WordNet's noun graph is a taxonomy. The 2026-10-19 coverage diagnostic found
that 7 of 11 missed dev2 noun swaps (``delay~latency``, ``load~utilization``,
``changeover~rotation``, ``capability~feature``) have no WordNet noun path
<= 2 at all, so a stricter or looser WordNet gate cannot fix them. What they
need is *usage* synonymy: words people use in place of each other.

Source: the Datamuse API ``/words?ml=<word>`` ("means like") constraint
(https://www.datamuse.com/api/). Per its documentation, single-word ``ml``
results combine WordNet 3.0, dozens of online dictionaries crawled by
OneLook, the PPDB "XXL" lexical paraphrases, and word2vec backfill, ranked by
estimated strength of the relation. That makes it the closest available
stand-in for a paraphrase database (the PPDB download host no longer answers).

How the snapshot is built (``scripts/fetch_datamuse_ml.py`` +
``scripts/build_datamuse_neighbours.py``): the API is queried **only with
corpus words** (the 440 plain content words of ``data/corpus``), never with an
eval word. Each response is a ranked list of words that mean like the corpus
word. The committed table inverts those lists: every single-word result maps
to the corpus words whose list it appeared in, with its rank there (and the
corpus-word -> corpus-word direction for known words). Nothing is filtered or
added by hand, so the table's contents depend only on Datamuse and the corpus.

``DatamuseSense.neighbours`` has the backoff interface of
``WordNetNounSense`` (``Neighbour`` tuples, the same ``known`` / ``lone`` /
``all`` scopes) and plugs into the same noun read-path slot. Its gate (rank
cut-off, neighbour count, noun-tag filter, scope) is calibrated on clean +
dev + dev2 ``calib`` rows only (``datamuse_dev2.py``). Returning nothing is
the safe answer.

**Corpus-context gate** (``context_min``, off at 0; added 2026-10-21). The
2026-10-20 coverage diagnostic found precision, not coverage, was the limit:
neighbours come in the source's rank order for the *corpus* word, so noisy
words win (``delay -> wait`` before ``latency``, ``plan -> chart``). With
``context_min = k > 0`` a candidate corpus word ``c`` for query word ``q`` is
kept only if some corpus chunk contains ``c`` together with at least ``k`` of
the query's *other* corpus words (``set_context``), and candidates are
re-ranked by that co-occurrence count before the source rank. It uses only
the corpus and the query, so it needs no eval input; with no context set
(e.g. the retrieval rewrite) a gated backoff returns nothing.
"""

from __future__ import annotations

import gzip
import io
import json
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from pathlib import Path

from ops_copilot.semantic import Neighbour
from ops_copilot.text import fold_token, is_identifier

DATA_DIR = Path(__file__).resolve().parents[2] / "data" / "datamuse"
DEFAULT_TABLE = DATA_DIR / "ml_neighbours.json.gz"
SOURCE_NAME = "Datamuse API /words means-like (ml) constraint"
SOURCE_URL = "https://api.datamuse.com/words?ml={word}&max={max}&md=p"
SOURCE_DOCS = "https://www.datamuse.com/api/"
SOURCE_ATTRIBUTION = (
    "Datamuse API (datamuse.com); ml results draw on WordNet 3.0, OneLook "
    "dictionaries, PPDB XXL lexical paraphrases and word2vec"
)
MAX_RESULTS = 100
MIN_WORD_LEN = 3
# Row format of the committed table: [corpus_word, rank, noun_tag, direction].
# rank is 1-based in the source response; noun_tag is 1 when Datamuse tagged
# the result word "n" in that response; direction is "rev" (the key appeared
# in the corpus word's list) or "fwd" (the key is a corpus word and the
# corpus word appeared in its list).
ROW_FORMAT = ("corpus_word", "rank", "noun_tag", "direction")


def _plain(word: str) -> bool:
    return word.isalpha() and word.islower() and len(word) >= MIN_WORD_LEN


def parse_response(items: Iterable[Mapping]) -> list[tuple[str, int, bool]]:
    """Datamuse result objects -> (word, 1-based rank, noun tag) for plain single words.

    The rank is the item's position in the full response (multi-word or
    non-alphabetic results keep their slot, so ranks are the source's).
    """
    out: list[tuple[str, int, bool]] = []
    seen: set[str] = set()
    for i, it in enumerate(items, start=1):
        w = str(it.get("word", ""))
        if not _plain(w) or w in seen:
            continue
        seen.add(w)
        tags = it.get("tags") or ()
        out.append((w, i, "n" in tags))
    return out


def build_neighbour_table(
    responses: Mapping[str, Iterable[Mapping]], targets: Iterable[str]
) -> dict[str, list[list]]:
    """Invert per-corpus-word ``ml`` lists into word -> corpus-word rows.

    ``responses`` maps each queried corpus word to its raw result list. Every
    plain result word ``x`` in the list of corpus word ``c`` at rank ``r``
    gives ``table[x] += [c, r, noun, "rev"]``; when ``x`` is itself a corpus
    word, ``table[c] += [x, r, noun, "fwd"]`` too. The best (lowest) rank per
    (key, corpus word) is kept; rows sort by (rank, corpus word).
    """
    tset = frozenset(targets)
    best: dict[str, dict[str, tuple[int, bool, str]]] = {}

    def put(key: str, c: str, rank: int, noun: bool, d: str) -> None:
        if key == c:
            return
        row = best.setdefault(key, {})
        prev = row.get(c)
        if prev is None or (rank, d) < (prev[0], prev[2]):
            row[c] = (rank, noun, d)

    for c in sorted(responses):
        if c not in tset:
            raise ValueError(f"response for {c!r}, which is not a corpus word")
        for x, rank, noun in parse_response(responses[c]):
            put(x, c, rank, noun, "rev")
            if x in tset:
                put(c, x, rank, noun, "fwd")
    table: dict[str, list[list]] = {}
    for key in sorted(best):
        rows = sorted(
            ([c, rank, int(noun), d] for c, (rank, noun, d) in best[key].items()),
            key=lambda r: (r[1], r[0]),
        )
        table[key] = rows
    return table


def dump_table(table: dict, meta: dict, path: str | Path) -> None:
    """gzip JSON with zero mtime (byte-identical rebuilds)."""
    payload = json.dumps(
        {"meta": meta, "neighbours": table},
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    buf = io.BytesIO()
    with gzip.GzipFile(fileobj=buf, mode="wb", mtime=0, compresslevel=9) as gz:
        gz.write(payload)
    Path(path).write_bytes(buf.getvalue())


@dataclass(frozen=True)
class DatamuseTable:
    meta: dict
    neighbours: dict[str, tuple[tuple[str, int, bool, str], ...]]

    @classmethod
    def load(cls, path: str | Path | None = None) -> "DatamuseTable":
        with gzip.open(Path(path) if path else DEFAULT_TABLE, "rt", encoding="utf-8") as fh:
            raw = json.load(fh)
        nb = {
            w: tuple((str(c), int(r), bool(n), str(d)) for c, r, n, d in rows)
            for w, rows in raw["neighbours"].items()
        }
        return cls(dict(raw["meta"]), nb)


_TABLES: dict[str, DatamuseTable] = {}


def load_table(path: str | Path | None = None) -> DatamuseTable:
    key = str(Path(path) if path else DEFAULT_TABLE)
    if key not in _TABLES:
        _TABLES[key] = DatamuseTable.load(key)
    return _TABLES[key]


@dataclass
class DatamuseSense:
    """Map a query word onto corpus words whose Datamuse ``ml`` list ranks it highly.

    Gate: ``rank <= max_rank`` in the corpus word's list; with ``noun_only``
    the word must carry Datamuse's noun tag there. Scopes as in
    ``WordNetNounSense``: ``known_only`` expands corpus words only (grounding
    alts); ``lone_unknown`` also maps an unknown word when the grounder finds
    it is the query's only unknown content word.
    """

    term_kind = "datamuse_ml"

    max_rank: int = 10
    max_neighbours: int = 1
    noun_only: bool = False
    known_only: bool = False
    lone_unknown: bool = False
    suspend_unknown: bool = False
    corpus_words: frozenset[str] | None = None
    table: DatamuseTable | None = None
    # Corpus-context gate: 0 = off; k > 0 needs a chunk holding the candidate
    # and >= k other query words. ``doc_words`` = content tokens per chunk.
    context_min: int = 0
    doc_words: tuple[frozenset[str], ...] | None = None
    context: frozenset[str] | None = None
    # False: corpus words get no Datamuse alternatives (only unknown words are
    # mapped). Added after the 2026-10-21 sweep found revert -> returning
    # opening an ungrounded trap; True keeps the original behaviour.
    expand_known: bool = True
    _cache: dict[tuple, tuple[Neighbour, ...]] = field(default_factory=dict, repr=False)

    def __post_init__(self) -> None:
        if self.table is None:
            self.table = load_table()
        if self.max_rank < 1:
            raise ValueError("max_rank must be >= 1")
        if self.max_neighbours < 1:
            raise ValueError("max_neighbours must be >= 1")
        if self.context_min < 0:
            raise ValueError("context_min must be >= 0")
        if self.context_min and self.doc_words is None:
            raise ValueError("context_min > 0 needs doc_words (content tokens per corpus chunk)")
        self._docs_of: dict[str, list[int]] = {}
        for i, words in enumerate(self.doc_words or ()):
            for w in words:
                self._docs_of.setdefault(w, []).append(i)
        self.source_vocab: frozenset[str] = frozenset(self.table.meta.get("corpus_words") or ())

    @staticmethod
    def lookupable(token: str) -> bool:
        return token.isalpha() and not is_identifier(token) and len(token) >= MIN_WORD_LEN

    def _rows(self, tok: str) -> tuple[tuple[str, int, bool, str], ...]:
        rows = self.table.neighbours.get(tok)
        if rows is None:
            rows = self.table.neighbours.get(fold_token(tok))
        return rows or ()

    def context_support(self, word: str, query_token: str) -> int:
        """Most other query corpus words sharing one chunk with ``word`` (0 if none)."""
        others = (self.context or frozenset()) - {query_token, word}
        if not others or self.doc_words is None:
            return 0
        return max((len(self.doc_words[i] & others) for i in self._docs_of.get(word, ())), default=0)

    def neighbours(self, token: str) -> tuple[Neighbour, ...]:
        if not self.lookupable(token):
            return ()
        tok = token.lower()
        if tok not in self.source_vocab and (self.known_only or self.suspend_unknown):
            return ()
        if tok in self.source_vocab and not self.expand_known:
            return ()
        if self.context_min and self.context is None:
            return ()
        key = (tok, self.context) if self.context_min else (tok,)
        if key in self._cache:
            return self._cache[key]
        cands: list[tuple[int, int, str]] = []
        for word, rank, noun, _d in self._rows(tok):
            if word == tok or rank > self.max_rank:
                continue
            if self.noun_only and not noun:
                continue
            if self.corpus_words is not None and word not in self.corpus_words:
                continue
            if self.context_min:
                sup = self.context_support(word, tok)
                if sup < self.context_min:
                    continue
                cands.append((-sup, rank, word))
            else:
                cands.append((0, rank, word))
        if self.context_min:
            cands.sort()
        out = tuple(Neighbour(w, 1.0 / r, "datamuse_ml") for _s, r, w in cands[: self.max_neighbours])
        self._cache[key] = out
        return out

    def set_context(self, words: frozenset[str] | None) -> None:
        self.context = None if words is None else frozenset(words)

    def set_suspend_unknown(self, value: bool) -> None:
        self.suspend_unknown = bool(value)
