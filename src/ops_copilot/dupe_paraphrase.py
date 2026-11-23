"""Duplicate-question paraphrases: an ops synonym table mined from closed-as-duplicate titles.

Every outside resource tried so far (counter-fitted vectors, Datamuse, WordNet, Wiktionary,
Stack Exchange tag synonyms, and their agreement on Nov 11) is either general English or
lists tags, not wordings, and none of them holds the ops senses the README keeps naming
(Nov 11 weaknesses: "an ops synonym model needs ops text with paraphrase signal").

A question closed as a duplicate on Server Fault, Super User, Unix & Linux, Ask Ubuntu,
DBA, Information Security, DevOps or Network Engineering is exactly that signal: a
moderator or several high-reputation users judged that two people asked the same thing,
and the two titles are two wordings of it. ``scripts/fetch_se_duplicates.py`` snapshots
the closed questions of those sites with no eval- or corpus-driven filter;
``scripts/build_dupe_paraphrase.py`` reduces the title pairs to the word table committed
in ``data/dupes/`` (word statistics only, no titles).

The alignment is deliberately simple and fixed before any eval row was scored:

- each pair (duplicate title, original title) is cut to plain alphabetic content words
  (``content_tokens``, length >= ``MIN_WORD_LEN``, plural-folded), and only the words that
  appear on **one side only** take part (shared words are context, not paraphrase);
- ``cross[a, b]`` counts pairs where ``a`` is on one side only and ``b`` on the other side
  only; ``same[a, b]`` counts titles where ``a`` and ``b`` sit together. A substitute
  replaces a word, so it should be seen across a pair much more often than inside one
  title; topical neighbours (``nginx`` / ``proxy``) co-occur inside titles;
- the association of a cross pair is Dunning's log-likelihood ratio G² over the
  one-side-only events (``n_pairs`` pairs, ``df[a]``, ``df[b]``, ``cross[a, b]``), positive
  associations only.

Lookups are symmetric (``a`` -> ``b`` and ``b`` -> ``a`` share one row) and return corpus
words only. The gates (minimum cross count, G² floor, cross / same ratio) are knobs whose
arms are fixed in ``dupe_paraphrase_protocol.py``.
"""

from __future__ import annotations

import gzip
import hashlib
import io
import json
import math
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable

from ops_copilot.semantic import Neighbour
from ops_copilot.text import content_tokens, fold_token, is_identifier

DATA_DIR = Path(__file__).resolve().parents[2] / "data" / "dupes"
DEFAULT_TABLE = DATA_DIR / "se_duplicate_paraphrase.json.gz"
DUPLICATE_REASONS = frozenset({"duplicate", "exact duplicate"})
MIN_WORD_LEN = 3
# Table build floor (kept rows): at least this many cross pairs and positive G².
BUILD_MIN_CROSS = 2
BUILD_MAX_PER_WORD = 40
SCOPES = ("known", "lone", "all")


def title_words(title: str) -> frozenset[str]:
    """Plain alphabetic content words of a title, plural-folded (identifiers dropped)."""
    import html

    out = set()
    for t in content_tokens(html.unescape(title or "")):
        if t.isalpha() and not is_identifier(t) and len(t) >= MIN_WORD_LEN:
            out.add(fold_token(t))
    return frozenset(out)


def duplicate_pairs(pages: Iterable[dict]) -> list[tuple[str, int, str, str]]:
    """(site, question id, duplicate title, original title) for every duplicate closure.

    ``pages`` are raw API bodies with a ``site`` key added by the caller. A question that
    names several originals gives one pair per original; repeats of a question id (the
    same question on several sort orders) are dropped.
    """
    seen: set[tuple[str, int, int]] = set()
    out = []
    for body in pages:
        site = body["site"]
        for q in body.get("items", []):
            if str(q.get("closed_reason", "")).lower() not in DUPLICATE_REASONS:
                continue
            for o in (q.get("closed_details") or {}).get("original_questions", []) or []:
                key = (site, int(q["question_id"]), int(o["question_id"]))
                if key in seen or not o.get("title"):
                    continue
                seen.add(key)
                out.append((site, int(q["question_id"]), q["title"], o["title"]))
    return out


def g2(c: int, da: int, db: int, n: int) -> float:
    """Dunning log-likelihood ratio for a 2x2 table (positive association only, else 0)."""
    k = [[c, da - c], [db - c, n - da - db + c]]
    if min(min(r) for r in k) < 0 or n <= 0:
        return 0.0
    rows = [sum(r) for r in k]
    cols = [k[0][0] + k[1][0], k[0][1] + k[1][1]]
    if c * n <= da * db:
        return 0.0
    s = 0.0
    for i in range(2):
        for j in range(2):
            if k[i][j] > 0:
                s += k[i][j] * math.log(k[i][j] * n / (rows[i] * cols[j]))
    return 2.0 * s


def build_table(title_pairs: Iterable[tuple[str, str]]) -> dict:
    """Word statistics from (title, title) pairs: per word, its strongest cross partners."""
    pairs = [(title_words(a), title_words(b)) for a, b in title_pairs]
    n = len(pairs)
    df: Counter = Counter()      # pairs where the word is on one side only (G² margins)
    cross: Counter = Counter()   # unordered {a, b}: a one side only, b the other side only
    for a, b in pairs:
        oa, ob = a - b, b - a
        df.update(oa | ob)
        for x in oa:
            for y in ob:
                if x != y:
                    cross[(x, y) if x < y else (y, x)] += 1
    same: Counter = Counter()
    cand = {k for k, v in cross.items() if v >= BUILD_MIN_CROSS}
    cand_words = {w for k in cand for w in k}
    for a, b in pairs:
        for t in (a, b):
            ws = sorted(t & cand_words)
            for i, x in enumerate(ws):
                for y in ws[i + 1:]:
                    if (x, y) in cand:
                        same[(x, y)] += 1
    rows: dict[str, list] = {}
    for (x, y) in cand:
        c = cross[(x, y)]
        score = g2(c, df[x], df[y], n)
        if score <= 0:
            continue
        rec = [round(score, 3), c, same[(x, y)]]
        rows.setdefault(x, []).append([y, *rec])
        rows.setdefault(y, []).append([x, *rec])
    return {"n_pairs": n, "rows": _cap(rows)}


def _cap(rows: dict[str, list]) -> dict[str, list]:
    """Per word: strongest partners first (G² desc, then word), at most ``BUILD_MAX_PER_WORD``."""
    out = {}
    for w in sorted(rows):
        out[w] = sorted(rows[w], key=lambda r: (-r[1], r[0]))[:BUILD_MAX_PER_WORD]
    return out


def _columnar(rows: dict[str, list]) -> dict:
    """Each kept unordered pair once, as word indices plus three number columns.

    Lossless for the capped rows: a word's top ``BUILD_MAX_PER_WORD`` partners are all in the
    union, and the union holds nothing stronger for it, so ``_rows`` rebuilds them exactly.
    """
    pairs = {}
    for w, rs in rows.items():
        for other, score, cross, same in rs:
            pairs[(w, other) if w < other else (other, w)] = (score, cross, same)
    words = sorted({x for k in pairs for x in k})
    idx = {w: i for i, w in enumerate(words)}
    keys = sorted(pairs)
    return {"words": words, "a": [idx[a] for a, _ in keys], "b": [idx[b] for _, b in keys],
            "g2": [pairs[k][0] for k in keys], "cross": [pairs[k][1] for k in keys],
            "same": [pairs[k][2] for k in keys]}


def _rows(col: dict) -> dict[str, list]:
    words, rows = col["words"], {}
    for a, b, score, cross, same in zip(col["a"], col["b"], col["g2"], col["cross"], col["same"]):
        rows.setdefault(words[a], []).append([words[b], score, cross, same])
        rows.setdefault(words[b], []).append([words[a], score, cross, same])
    return _cap(rows)


def dump_table(table: dict, meta: dict, path: str | Path) -> str:
    """Byte-stable gzip (zero mtime) of the columnar pair list; returns the payload SHA-256."""
    body = {"meta": meta, "n_pairs": table["n_pairs"], "pairs": _columnar(table["rows"])}
    payload = json.dumps(body, sort_keys=True, separators=(",", ":")).encode("utf-8")
    buf = io.BytesIO()
    with gzip.GzipFile(fileobj=buf, mode="wb", mtime=0, compresslevel=9) as gz:
        gz.write(payload)
    Path(path).write_bytes(buf.getvalue())
    return hashlib.sha256(payload).hexdigest()


@dataclass(frozen=True)
class DupeTable:
    meta: dict
    n_pairs: int
    rows: dict

    def get(self, word: str) -> tuple:
        """``(other, g2, cross, same)`` rows for ``word`` (strongest first), folded fallback."""
        w = word.lower()
        got = self.rows.get(w) or self.rows.get(fold_token(w))
        return tuple(tuple(r) for r in got) if got else ()


_CACHE: dict[str, DupeTable] = {}


def load_table(path: str | Path = DEFAULT_TABLE) -> DupeTable:
    key = str(path)
    if key not in _CACHE:
        raw = gzip.decompress(Path(path).read_bytes())
        d = json.loads(raw)
        _CACHE[key] = DupeTable(d["meta"], d["n_pairs"], _rows(d["pairs"]))
    return _CACHE[key]


@dataclass
class DupeParaphraseSense:
    """Corpus words that duplicate-question titles swap for a query word.

    A candidate needs ``cross >= min_cross`` pairs, ``G² >= min_g2`` and
    ``cross / (same + 1) >= min_ratio`` (seen as a replacement more often than as a
    neighbour in one title). Scopes as in ``WordNetNounSense``: ``known`` expands corpus
    words only, ``lone`` also maps an unknown word when it is the query's only unknown
    content word, ``all`` maps every unknown word. No candidate means the word stays a
    high-weight unknown and grounding refuses as before.
    """

    corpus_words: frozenset[str]
    table: DupeTable
    min_cross: int = 3
    min_g2: float = 15.13
    min_ratio: float = 2.0
    scope: str = "known"
    max_neighbours: int = 1
    suspend_unknown: bool = False
    _cache: dict[str, tuple[Neighbour, ...]] = field(default_factory=dict, repr=False)

    term_kind = "dupe_paraphrase"

    def __post_init__(self) -> None:
        if self.scope not in SCOPES:
            raise ValueError(f"scope must be one of {SCOPES}, got {self.scope!r}")
        if self.min_cross < BUILD_MIN_CROSS:
            raise ValueError(f"min_cross must be >= the build floor {BUILD_MIN_CROSS}")
        if self.max_neighbours < 1:
            raise ValueError("max_neighbours must be >= 1")

    @classmethod
    def from_corpus(cls, corpus_texts: list[str], table: DupeTable | None = None, **kw) -> "DupeParaphraseSense":
        from ops_copilot.word_vectors import corpus_words

        return cls(frozenset(corpus_words(corpus_texts)), table or load_table(), **kw)

    @property
    def lone_unknown(self) -> bool:
        return self.scope == "lone"

    def set_suspend_unknown(self, value: bool) -> None:
        self.suspend_unknown = bool(value)

    @staticmethod
    def lookupable(token: str) -> bool:
        return token.isalpha() and not is_identifier(token) and len(token) >= MIN_WORD_LEN

    def _in_corpus(self, w: str) -> str | None:
        if w in self.corpus_words:
            return w
        for v in (w + "s", w + "es"):
            if v in self.corpus_words and fold_token(v) == w:
                return v
        return None

    def candidates(self, token: str) -> list[tuple[str, float, int, int]]:
        """Gate-passing corpus words for ``token``: ``(word, g2, cross, same)``, strongest first."""
        tok = token.lower()
        same_word = {tok, fold_token(tok)}
        out = []
        for other, score, cross, same in self.table.get(tok):
            if other in same_word or cross < self.min_cross or score < self.min_g2:
                continue
            if cross / (same + 1) < self.min_ratio:
                continue
            word = self._in_corpus(other)
            if word is not None and word not in same_word:
                out.append((word, float(score), int(cross), int(same)))
        out.sort(key=lambda r: (-r[1], r[0]))
        return out

    def neighbours(self, token: str) -> tuple[Neighbour, ...]:
        if not self.lookupable(token):
            return ()
        tok = token.lower()
        known = tok in self.corpus_words or fold_token(tok) in self.corpus_words
        if not known and (self.scope == "known" or self.suspend_unknown):
            return ()
        if tok in self._cache:
            return self._cache[tok]
        out = tuple(Neighbour(w, s, "dupe_paraphrase") for w, s, _, _ in self.candidates(tok)[: self.max_neighbours])
        self._cache[tok] = out
        return out
