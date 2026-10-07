"""Wiktionary computing senses: an external, ops-domain dictionary backoff.

Stack Exchange tag synonyms (``tag_synonyms.py``) turned out to name products
and tools, not paraphrases: they offered a substitute for 0 of the 63 dev
replacement words. A dictionary does carry the senses an operator means.
English Wiktionary labels senses by domain, e.g. *bounce* has a sense
labelled ``(computing)``, and those senses have a gloss written for readers
and sometimes a synonym list. Wiktionary editors never saw this eval.

Source: the Wiktextract dump of English Wiktionary published by kaikki.org
(Ylonen, LREC 2022), CC BY-SA 4.0 / GFDL. ``scripts/build_wiktionary_senses.py``
streams the 3.3 GB JSONL once and keeps *every* English sense whose topic is
in ``OPS_TOPICS`` (computing, software, networking, databases, ...), with no
filtering by eval or corpus words: headword, part of speech, topic, the
sense's single-word synonyms and its first gloss (truncated). Tests and CI
read only the committed extract in ``data/wiktionary/``.

``build_sense_table`` turns the extract into substitutes, restricted to corpus
words only at load time:

- ``synonym``: a corpus word listed as a synonym of the headword in a domain
  sense (score 2);
- ``gloss_head``: the first content word of a domain sense's gloss, when it is
  a corpus word ("bounce: (computing) To restart a device" -> restart;
  score 1). Glosses define by genus word, so the head is usually the hypernym
  or the plain-English equivalent.
"""

from __future__ import annotations

import gzip
import hashlib
import io
import json
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parents[2] / "data" / "wiktionary"
DEFAULT_EXTRACT = DATA_DIR / "computing_senses.json.gz"
SOURCE_URL = "https://kaikki.org/dictionary/English/kaikki.org-dictionary-English.jsonl"
SOURCE_NAME = "Wiktextract English Wiktionary dump (kaikki.org)"
# Domain labels of running systems. Graphics, games, computing theory and
# programming-language labels are left out on purpose (not operations).
OPS_TOPICS: tuple[str, ...] = (
    "computing",
    "computer",
    "computer-hardware",
    "computer-software",
    "software",
    "programming",
    "networking",
    "databases",
    "information-technology",
    "telecommunications",
)
MIN_WORD_LEN = 3
GLOSS_CHARS = 200
# Payload SHA-256 of the committed extract, built 2026-10-07 from the dump
# with SHA-256 9978ce34...c02195 (1,492,836 entries): 6,717 domain senses of
# 5,551 headwords.
EXTRACT_SHA256 = "ca42ffd432a04764529b05a724876323f8f2e2066f91003e418af306f6c89e2f"
EXTRACT_N_SENSES = 6717


def headword_ok(word: str) -> bool:
    return len(word) >= MIN_WORD_LEN and word.isascii() and word.isalpha()


def extract_senses(entry: dict) -> list[dict]:
    """Domain senses of one Wiktextract entry (empty if not English / not plain)."""
    if entry.get("lang_code") != "en":
        return []
    word = str(entry.get("word", ""))
    if not headword_ok(word.lower()) or word != word.lower():
        return []
    out: list[dict] = []
    for sense in entry.get("senses", []):
        topics = [t for t in sense.get("topics", []) if t in OPS_TOPICS]
        glosses = sense.get("glosses") or []
        if not topics or not glosses:
            continue
        syns = sorted(
            {
                s["word"].lower()
                for s in sense.get("synonyms", [])
                if isinstance(s.get("word"), str) and headword_ok(s["word"].lower())
            }
        )
        out.append(
            {
                "word": word,
                "pos": str(entry.get("pos", "")),
                "topic": topics[0],
                "synonyms": syns,
                "gloss": str(glosses[0])[:GLOSS_CHARS],
            }
        )
    return out


def _payload(senses: list[dict], meta: dict) -> bytes:
    rows = sorted(senses, key=lambda s: (s["word"], s["pos"], s["topic"], s["gloss"], s["synonyms"]))
    meta = dict(meta) | {"n_senses": len(rows), "n_words": len({r["word"] for r in rows})}
    return json.dumps(
        {"meta": meta, "senses": rows}, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")


def dump_extract(senses: list[dict], meta: dict, path: str | Path) -> str:
    """Byte-stable gzip extract (zero mtime); returns the payload SHA-256."""
    payload = _payload(senses, meta)
    buf = io.BytesIO()
    with gzip.GzipFile(fileobj=buf, mode="wb", mtime=0, compresslevel=9) as gz:
        gz.write(payload)
    Path(path).write_bytes(buf.getvalue())
    return hashlib.sha256(payload).hexdigest()


def load_extract(path: str | Path | None = None) -> dict:
    with gzip.open(Path(path) if path else DEFAULT_EXTRACT, "rb") as fh:
        raw = fh.read()
    data = json.loads(raw)
    data["sha256"] = hashlib.sha256(raw).hexdigest()
    return data


# --- substitute table ---------------------------------------------------------

# Glosses that *are* a pointer to another word ("Abbreviation of configuration.").
POINTER_PREFIXES: tuple[str, ...] = (
    "synonym of",
    "abbreviation of",
    "short for",
    "clipping of",
    "initialism of",
    "acronym of",
    "ellipsis of",
    "contraction of",
    "alternative form of",
    "alternative spelling of",
)
SCORE_SYNONYM = 2
SCORE_GLOSS_HEAD = 1


def gloss_head(gloss: str) -> tuple[str | None, bool]:
    """(first content word of the gloss, whether the gloss is a pointer)."""
    from ops_copilot.text import content_tokens, normalize_text

    text = normalize_text(gloss)
    pointer = False
    for pre in POINTER_PREFIXES:
        if text.startswith(pre + " "):
            text, pointer = text[len(pre) + 1 :], True
            break
    for tok in content_tokens(text):
        if tok.isalpha():
            return tok, pointer
        return None, pointer  # an identifier / number head: no plain word
    return None, pointer


def build_sense_table(
    senses: list[dict],
    targets: set[str] | frozenset[str],
    *,
    use_gloss_heads: bool = True,
) -> dict[str, tuple[tuple[str, int], ...]]:
    """headword -> ((corpus word, score), ...), best first.

    Score 2: listed synonym, or the word a pointer gloss names. Score 1: the
    gloss head word. A headword never maps to itself or an inflection of
    itself; the best score over its senses is kept; ties break by spelling.
    """
    from ops_copilot.tag_synonyms import is_inflection
    from ops_copilot.text import fold_token

    def target_of(word: str) -> str | None:
        for cand in (word, fold_token(word), word + "s"):
            if cand in targets:
                return cand
        return None

    best: dict[str, dict[str, int]] = {}
    for s in senses:
        head = s["word"]
        cands: list[tuple[str, int]] = [(w, SCORE_SYNONYM) for w in s["synonyms"]]
        g, pointer = gloss_head(s["gloss"])
        if g is not None and (pointer or use_gloss_heads):
            cands.append((g, SCORE_SYNONYM if pointer else SCORE_GLOSS_HEAD))
        for w, score in cands:
            t = target_of(w)
            if t is None or t == head or is_inflection(head, t):
                continue
            row = best.setdefault(head, {})
            row[t] = max(row.get(t, 0), score)
    return {
        h: tuple(sorted(row.items(), key=lambda ts: (-ts[1], ts[0])))
        for h, row in sorted(best.items())
    }


_TABLE_CACHE: dict[tuple, dict] = {}


class WiktionarySenseBackoff:
    """Map a query word onto corpus words its computing senses point to (or none).

    ``neighbours`` has the ``semantic.SemanticBackoff`` interface; a
    neighbour's similarity is its score (2 synonym / pointer, 1 gloss head).
    Only scores >= ``min_score`` are returned, at most ``max_neighbours``.
    Identifiers, numbers and short tokens are never looked up.
    """

    def __init__(
        self,
        corpus_texts: list[str],
        *,
        min_score: int = SCORE_GLOSS_HEAD,
        max_neighbours: int = 1,
        extract: dict | None = None,
    ) -> None:
        from ops_copilot.word_vectors import corpus_words, words_fingerprint

        self.corpus_words: frozenset[str] = frozenset(corpus_words(corpus_texts))
        self.min_score = int(min_score)
        self.max_neighbours = int(max_neighbours)
        use_heads = self.min_score <= SCORE_GLOSS_HEAD
        if extract is not None:
            self.table = build_sense_table(extract["senses"], self.corpus_words, use_gloss_heads=use_heads)
        else:
            key = (words_fingerprint(sorted(self.corpus_words)), use_heads)
            if key not in _TABLE_CACHE:
                _TABLE_CACHE[key] = build_sense_table(
                    load_extract()["senses"], self.corpus_words, use_gloss_heads=use_heads
                )
            self.table = _TABLE_CACHE[key]
        self._cache: dict[str, tuple] = {}

    @staticmethod
    def lookupable(token: str) -> bool:
        from ops_copilot.text import is_identifier

        return token.isalpha() and not is_identifier(token) and len(token) >= MIN_WORD_LEN

    def neighbours(self, token: str) -> tuple:
        from ops_copilot.semantic import Neighbour
        from ops_copilot.text import fold_token

        tok = token.lower()
        if tok in self._cache:
            return self._cache[tok]
        found: tuple = ()
        if self.lookupable(tok):
            rows = self.table.get(tok) or self.table.get(fold_token(tok), ())
            picked = [
                Neighbour(w, float(s), "wiktionary")
                for w, s in rows
                if s >= self.min_score and w in self.corpus_words and w != tok
            ]
            found = tuple(picked[: self.max_neighbours])
        self._cache[tok] = found
        return found
