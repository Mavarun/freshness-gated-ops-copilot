"""WordNet noun-sense backoff: an external, hand-curated sense inventory.

Held-out ANSWER rows have been 0 of 9 for every read-path backoff so far.
The two pairs named in the README (``lag~latency``, ``health~status``) have
no bridge in the counter-fitted vectors (``latency`` is out of vocabulary),
the Stack Exchange vectors (wrong senses: LACP, wellness) or the Wiktionary
computing extract (gloss cosine 0.49 < gate). The last slice showed the only
honest way forward is a *larger external* noun-sense resource that nobody
writing it saw this eval.

Source: Princeton WordNet 3.0 noun synsets (``data.noun`` / ``index.noun``,
WordNet 3.0 license, BSD-style). WordNet groups lemmas into synsets and
links synsets by hypernymy, so sense relations are explicit rather than
inferred from co-occurrence:

- ``health`` (sense 1, "the general condition of body and mind") has the
  hypernym synset {condition, status};
- ``lag`` (sense 3, {interim, meantime, lag}) and ``latency`` (sense 2,
  {reaction time, response time, latency}) are both direct hyponyms of
  {time interval, interval}.

What is committed (``data/wordnet/wn_noun_neighbours.json.gz``, built by
``scripts/build_wordnet_neighbours.py``): for *every* single-word WordNet
noun lemma, the corpus content words reachable from any of its senses by

- ``syn``   same synset                          (path 0)
- ``hyper`` lemma of a direct hypernym           (path 1)
- ``hypo``  lemma of a direct hyponym            (path 1)
- ``sib``   co-hyponym under a direct hypernym   (path 2, with the hypernym's
  hyponym *fan-out*, so a sibling under a crowded genus can be gated off)

The table is not filtered by eval words; its contents depend only on WordNet
and the corpus. ``WordNetNounSense.neighbours`` has the backoff interface
used by grounding and retrieve (``Neighbour`` tuples). Its gate (max path,
max sibling fan-out, neighbour count) is calibrated on clean golden + *dev*
rows only (``wordnet_sense_calibration.py``); held-out rows decide go / no-go
once. Returning nothing is the safe answer.
"""

from __future__ import annotations

import gzip
import io
import json
from collections import defaultdict
from collections.abc import Iterable, Iterator
from dataclasses import dataclass, field
from pathlib import Path

from ops_copilot.semantic import Neighbour
from ops_copilot.text import fold_token, is_identifier

DATA_DIR = Path(__file__).resolve().parents[2] / "data" / "wordnet"
DEFAULT_TABLE = DATA_DIR / "wn_noun_neighbours.json.gz"
SOURCE_NAME = "Princeton WordNet 3.0 (nltk_data corpora/wordnet.zip)"
SOURCE_URL = "https://raw.githubusercontent.com/nltk/nltk_data/gh-pages/packages/corpora/wordnet.zip"
# SHA-256 of wordnet.zip as fetched by nltk.download("wordnet").
SOURCE_SHA256 = "cbda5ea6eef7f36a97a43d4a75f85e07fccbb4f23657d27b4ccbc93e2646ab59"
SOURCE_LICENSE = "WordNet 3.0 license (Princeton University, BSD-style)"
MIN_WORD_LEN = 3
HYPERNYM_PTRS = ("@", "@i")
REL_ORDER = {"syn": 0, "hyper": 1, "hypo": 1, "sib": 2}


@dataclass(frozen=True)
class Synset:
    offset: str
    lemmas: tuple[str, ...]
    hypernyms: tuple[str, ...]
    gloss: str = ""


def parse_data_noun(lines: Iterable[str]) -> dict[str, Synset]:
    """Parse WordNet ``data.noun`` lines (license header lines start with spaces)."""
    out: dict[str, Synset] = {}
    for line in lines:
        if not line.strip() or line.startswith("  "):
            continue
        head, _, gloss = line.partition(" | ")
        f = head.split()
        offset = f[0]
        n_words = int(f[3], 16)
        lemmas = tuple(f[4 + 2 * i].lower() for i in range(n_words))
        i = 4 + 2 * n_words
        n_ptr = int(f[i])
        i += 1
        hyper: list[str] = []
        for _ in range(n_ptr):
            sym, tgt, pos = f[i], f[i + 1], f[i + 2]
            if sym in HYPERNYM_PTRS and pos == "n":
                hyper.append(tgt)
            i += 4
        out[offset] = Synset(offset, lemmas, tuple(hyper), gloss.strip())
    return out


def parse_index_noun(lines: Iterable[str]) -> dict[str, tuple[str, ...]]:
    """Lemma -> synset offsets in WordNet sense order (most frequent first)."""
    out: dict[str, tuple[str, ...]] = {}
    for line in lines:
        if not line.strip() or line.startswith("  "):
            continue
        f = line.split()
        lemma = f[0].lower()
        n_synsets = int(f[2])
        n_ptr = int(f[3])
        offs = f[4 + n_ptr + 2 :]
        out[lemma] = tuple(offs[:n_synsets])
    return out


def _plain(lemma: str) -> bool:
    return lemma.isalpha() and len(lemma) >= MIN_WORD_LEN


def iter_relations(
    synsets: dict[str, Synset], senses: dict[str, tuple[str, ...]]
) -> Iterator[tuple[str, str, str, int, int]]:
    """Yield (lemma, related_lemma, relation, fan_out, sense_rank) for every lemma."""
    hyponyms: dict[str, list[str]] = defaultdict(list)
    for off, s in synsets.items():
        for h in s.hypernyms:
            hyponyms[h].append(off)
    for lemma in sorted(senses):
        if not _plain(lemma):
            continue
        for rank, off in enumerate(senses[lemma]):
            s = synsets.get(off)
            if s is None:
                continue
            for w in s.lemmas:
                yield lemma, w, "syn", 0, rank
            for h in s.hypernyms:
                for w in synsets[h].lemmas:
                    yield lemma, w, "hyper", 0, rank
                fan = len(hyponyms[h])
                for sib in hyponyms[h]:
                    if sib == off:
                        continue
                    for w in synsets[sib].lemmas:
                        yield lemma, w, "sib", fan, rank
            for h in hyponyms.get(off, ()):
                for w in synsets[h].lemmas:
                    yield lemma, w, "hypo", 0, rank


def _key(rel: str, fan: int, rank: int) -> tuple[int, int, int]:
    return (REL_ORDER[rel], fan, rank)


def build_neighbour_table(
    synsets: dict[str, Synset],
    senses: dict[str, tuple[str, ...]],
    targets: Iterable[str],
) -> dict[str, list[list]]:
    """Every WordNet lemma -> its best relation to each reachable corpus word.

    Rows are ``[corpus_word, relation, path, fan_out, sense_rank]`` sorted by
    (path, fan_out, sense_rank, word). Only lemmas with at least one corpus
    neighbour are kept; nothing is filtered by eval words.
    """
    tset = frozenset(targets)
    best: dict[str, dict[str, tuple[str, int, int]]] = defaultdict(dict)
    for lemma, w, rel, fan, rank in iter_relations(synsets, senses):
        if w == lemma or w not in tset:
            continue
        prev = best[lemma].get(w)
        if prev is None or _key(rel, fan, rank) < _key(*prev):
            best[lemma][w] = (rel, fan, rank)
    table: dict[str, list[list]] = {}
    for lemma, rows in best.items():
        ordered = sorted(
            ([w, rel, REL_ORDER[rel], fan, rank] for w, (rel, fan, rank) in rows.items()),
            key=lambda r: (r[2], r[3], r[4], r[0]),
        )
        table[lemma] = ordered
    return dict(sorted(table.items()))


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
class WordNetTable:
    meta: dict
    neighbours: dict[str, tuple[tuple[str, str, int, int, int], ...]]

    @classmethod
    def load(cls, path: str | Path | None = None) -> "WordNetTable":
        with gzip.open(Path(path) if path else DEFAULT_TABLE, "rt", encoding="utf-8") as fh:
            raw = json.load(fh)
        nb = {
            w: tuple((str(t), str(rel), int(p), int(fan), int(rank)) for t, rel, p, fan, rank in rows)
            for w, rows in raw["neighbours"].items()
        }
        return cls(dict(raw["meta"]), nb)


_TABLES: dict[str, WordNetTable] = {}


def load_table(path: str | Path | None = None) -> WordNetTable:
    key = str(Path(path) if path else DEFAULT_TABLE)
    if key not in _TABLES:
        _TABLES[key] = WordNetTable.load(key)
    return _TABLES[key]


@dataclass
class WordNetNounSense:
    """Map a query noun onto corpus words that WordNet relates to one of its senses.

    Gate: relation path <= ``max_path`` (0 synonym, 1 hyper/hyponym, 2 sibling)
    and, for siblings, the shared hypernym's fan-out <= ``max_fanout`` (a
    crowded genus such as {time period} relates everything to everything).
    With ``known_only`` only corpus words are expanded (grounding alts for a
    known word missing from the evidence); unknown words get nothing.
    """

    term_kind = "wordnet_sense"

    max_path: int = 1
    max_fanout: int = 25
    max_neighbours: int = 1
    known_only: bool = False
    corpus_words: frozenset[str] | None = None
    table: WordNetTable | None = None
    _cache: dict[str, tuple[Neighbour, ...]] = field(default_factory=dict, repr=False)

    def __post_init__(self) -> None:
        if self.table is None:
            self.table = load_table()
        if self.max_path not in (0, 1, 2):
            raise ValueError("max_path must be 0, 1 or 2")
        # Words the table was built against (the corpus vocabulary).
        self.source_vocab: frozenset[str] = frozenset(self.table.meta.get("corpus_words") or ())

    @staticmethod
    def lookupable(token: str) -> bool:
        return token.isalpha() and not is_identifier(token) and len(token) >= MIN_WORD_LEN

    def _rows(self, token: str) -> tuple[tuple[str, str, int, int, int], ...]:
        tok = token.lower()
        rows = self.table.neighbours.get(tok)
        if rows is None:
            rows = self.table.neighbours.get(fold_token(tok), ())
        return rows

    def neighbours(self, token: str) -> tuple[Neighbour, ...]:
        if not self.lookupable(token):
            return ()
        tok = token.lower()
        if tok in self._cache:
            return self._cache[tok]
        if self.known_only and tok not in self.source_vocab:
            # An unknown word stays unknown: mapping it onto corpus words is
            # what turns clean NO_EVIDENCE traps into UNGROUNDED.
            self._cache[tok] = ()
            return ()
        out: list[Neighbour] = []
        for word, rel, path, fan, _rank in self._rows(tok):
            if word == tok or path > self.max_path:
                continue
            if rel == "sib" and fan > self.max_fanout:
                continue
            if self.corpus_words is not None and word not in self.corpus_words:
                continue
            score = 1.0 / (1.0 + path)
            out.append(Neighbour(word, score, f"wordnet_{rel}"))
            if len(out) >= self.max_neighbours:
                break
        self._cache[tok] = tuple(out)
        return self._cache[tok]


@dataclass
class ChainedNounSense:
    """First non-empty answer from several noun-sense backoffs (or ``None``)."""

    parts: tuple

    @classmethod
    def of(cls, *backoffs):
        live = tuple(b for b in backoffs if b is not None)
        if not live:
            return None
        if len(live) == 1:
            return live[0]
        return cls(live)

    @property
    def term_kind(self) -> str:
        return "noun_sense"

    def neighbours(self, token: str) -> tuple[Neighbour, ...]:
        for part in self.parts:
            got = part.neighbours(token)
            if got:
                return got
        return ()
