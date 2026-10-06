"""Counter-fitted word-vector backoff: an external synonym resource, offline.

Every synonym this repo understood so far was either written into a lexicon by
its author (``synonyms.py``) or learned from the 57-document corpus itself
(``semantic.py``), and neither generalises to words it was not given: held-out
synonym rows needing an answer or a write were 1 of 12 in the default config.
The README's stated next step was a resource *written by someone who has not
seen the eval*. This module is that resource.

Source: the counter-fitted word vectors of Mrkšić et al. (NAACL 2016,
"Counter-fitting Word Vectors to Linguistic Constraints"), 65,713 English
words x 300 dims. They start from Paragram-SL999 vectors and are pulled
together on PPDB 2.0 synonym pairs and pushed apart on WordNet / PPDB
antonym pairs, so cosine measures *substitutability* (SimLex-999 rho 0.74)
rather than topical relatedness: ``begin`` ~ ``start``, while antonyms such
as ``on`` / ``off`` are separated. It is the standard resource for
synonym-substitution attacks on NLP models for that reason. Nobody involved in
it saw this repo's eval, and its vocabulary is not filtered by eval words.

What is committed (``data/wordvec/cf_neighbours.json.gz``, built by
``scripts/build_word_neighbours.py``): for *every* word of the external
vocabulary, its nearest corpus content words with cosine >= ``floor``
(at most ``top_k``). The backoff only ever maps a query word onto a corpus
word, so this table is all it needs, and it is small (no 75 MB vectors in
git). The build records the source archive's SHA-256 and the corpus word
list, and a test fails if the corpus changes without a rebuild.

``WordVectorBackoff.neighbours`` has the ``semantic.SemanticBackoff``
interface: it returns at most ``max_neighbours`` corpus words whose cosine
clears ``min_similarity`` (threshold and neighbour count are calibrated on
clean golden + *dev* synonym rows only, ``word_vector_calibration.py``).
Returning nothing is the safe answer: the word stays an unknown, high-weight
term and grounding refuses as before. Identifiers, numbers and short tokens
are never looked up.
"""

from __future__ import annotations

import gzip
import hashlib
import io
import json
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from ops_copilot.semantic import Neighbour
from ops_copilot.text import content_tokens, fold_token, is_identifier

DATA_DIR = Path(__file__).resolve().parents[2] / "data" / "wordvec"
DEFAULT_TABLE = DATA_DIR / "cf_neighbours.json.gz"
SOURCE_URL = (
    "https://github.com/nmrksic/counter-fitting/raw/master/word_vectors/"
    "counter-fitted-vectors.txt.zip"
)
SOURCE_NAME = "counter-fitted-vectors (Mrksic et al., NAACL 2016)"
MIN_WORD_LEN = 3
TABLE_FLOOR = 0.50
TABLE_TOP_K = 5


def corpus_words(texts: Iterable[str]) -> list[str]:
    """Plain alphabetic corpus content words (the only targets a mapping may have)."""
    out = {
        t
        for text in texts
        for t in content_tokens(text)
        if t.isalpha() and not is_identifier(t) and len(t) >= MIN_WORD_LEN
    }
    return sorted(out)


def words_fingerprint(words: Sequence[str]) -> str:
    """Stable hash of a sorted word list (detects a corpus change)."""
    return hashlib.sha256("\n".join(sorted(words)).encode("utf-8")).hexdigest()[:16]


def read_text_vectors(lines: Iterable[str]) -> tuple[list[str], np.ndarray]:
    """``word v1 v2 ...`` lines -> (words, L2-normalised float32 matrix)."""
    words: list[str] = []
    rows: list[np.ndarray] = []
    for line in lines:
        parts = line.rstrip("\n").rstrip().split(" ")
        if len(parts) < 2:
            continue
        words.append(parts[0])
        rows.append(np.asarray(parts[1:], dtype=np.float32))
    if not rows:
        return [], np.zeros((0, 0), dtype=np.float32)
    mat = np.vstack(rows)
    norms = np.linalg.norm(mat, axis=1, keepdims=True)
    return words, mat / np.where(norms == 0, 1.0, norms)


def build_neighbour_table(
    words: Sequence[str],
    vectors: np.ndarray,
    targets: Sequence[str],
    *,
    floor: float = TABLE_FLOOR,
    top_k: int = TABLE_TOP_K,
    block: int = 8192,
) -> dict[str, list[list]]:
    """For every source word, its nearest ``targets`` with cosine >= ``floor``.

    ``targets`` missing from the source vocabulary cannot be reached and are
    skipped. A word is never its own neighbour. Ties break by spelling, and
    cosines are rounded to 4 decimals, so the table is byte-stable.
    """
    index = {w: i for i, w in enumerate(words)}
    tgt = [t for t in sorted(set(targets)) if t in index]
    if not tgt or len(words) == 0:
        return {}
    tmat = vectors[[index[t] for t in tgt]].T
    table: dict[str, list[list]] = {}
    for lo in range(0, len(words), block):
        sims = vectors[lo : lo + block] @ tmat
        for r in range(sims.shape[0]):
            word = words[lo + r]
            row = sims[r]
            cand = np.flatnonzero(row >= floor)
            if cand.size == 0:
                continue
            scored = sorted(
                ((tgt[j], round(float(row[j]), 4)) for j in cand if tgt[j] != word),
                key=lambda ts: (-ts[1], ts[0]),
            )[:top_k]
            if scored:
                table[word] = [[t, s] for t, s in scored]
    return table


def dump_table(table: dict, meta: dict, path: str | Path) -> None:
    """gzip-compressed JSON with a zero mtime (byte-identical rebuilds)."""
    payload = json.dumps(
        {"meta": meta, "neighbours": dict(sorted(table.items()))},
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    buf = io.BytesIO()
    with gzip.GzipFile(fileobj=buf, mode="wb", mtime=0, compresslevel=9) as gz:
        gz.write(payload)
    Path(path).write_bytes(buf.getvalue())


@dataclass(frozen=True)
class NeighbourTable:
    meta: dict
    neighbours: dict[str, tuple[tuple[str, float], ...]]

    @classmethod
    def load(cls, path: str | Path | None = None) -> "NeighbourTable":
        src = Path(path) if path else DEFAULT_TABLE
        with gzip.open(src, "rt", encoding="utf-8") as fh:
            raw = json.load(fh)
        nb = {w: tuple((str(t), float(s)) for t, s in rows) for w, rows in raw["neighbours"].items()}
        return cls(dict(raw["meta"]), nb)

    def __contains__(self, word: str) -> bool:
        return word in self.neighbours

    def get(self, word: str) -> tuple[tuple[str, float], ...]:
        return self.neighbours.get(word, ())


_TABLES: dict[str, NeighbourTable] = {}


def load_table(path: str | Path | None = None) -> NeighbourTable:
    """Process-wide cache of the committed table."""
    key = str(Path(path) if path else DEFAULT_TABLE)
    if key not in _TABLES:
        _TABLES[key] = NeighbourTable.load(key)
    return _TABLES[key]


class WordVectorBackoff:
    """Map a query word onto at most ``max_neighbours`` corpus substitutes (or none)."""

    def __init__(
        self,
        corpus_texts: list[str],
        *,
        table: NeighbourTable | None = None,
        min_similarity: float = 0.80,
        max_neighbours: int = 1,
    ) -> None:
        self.table = table if table is not None else load_table()
        self.corpus_words: frozenset[str] = frozenset(corpus_words(corpus_texts))
        if float(min_similarity) < float(self.table.meta.get("floor", 0.0)):
            raise ValueError(
                f"min_similarity {min_similarity} is below the table floor "
                f"{self.table.meta.get('floor')}: neighbours under it were not stored"
            )
        self.min_similarity = float(min_similarity)
        self.max_neighbours = int(max_neighbours)
        self._cache: dict[str, tuple[Neighbour, ...]] = {}

    @staticmethod
    def lookupable(token: str) -> bool:
        return token.isalpha() and not is_identifier(token) and len(token) >= MIN_WORD_LEN

    def neighbours(self, token: str) -> tuple[Neighbour, ...]:
        """Corpus words substitutable for ``token`` (never ``token`` itself)."""
        tok = token.lower()
        if tok in self._cache:
            return self._cache[tok]
        found: tuple[Neighbour, ...] = ()
        if self.lookupable(tok):
            rows = self.table.get(tok)
            if not rows and fold_token(tok) != tok:
                rows = self.table.get(fold_token(tok))
            picked = [
                Neighbour(w, s, "wordvec")
                for w, s in rows
                if s >= self.min_similarity and w in self.corpus_words and w != tok
            ]
            found = tuple(picked[: self.max_neighbours])
        self._cache[tok] = found
        return found
