"""Audit hand-written data resources for held-out synonym words.

Large external extracts (Wiktionary, Stack Exchange tag synonyms) may contain
held-out words, because they were not written with the split in mind. Resources
written by hand for this project may not: a seed that authors a held-out word
turns the held-out rows into training data. This module lists, per hand-written
resource, which held-out words appear (headword or any token).
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from ops_copilot.synonym_split import load_split
from ops_copilot.text import fold_token

ROOT = Path(__file__).resolve().parents[2]
HAND_WRITTEN = (
    "data/wiktionary/ops_noun_senses.json",
    "data/write/gloss_sense_dev.jsonl",
    "data/write/prototype_dev.jsonl",
    "data/glossary/ops_glossary.txt",
    "data/eval/synonym_dev2.jsonl",
    "data/eval/synonym_dev3.jsonl",
    "data/eval/synonym_dev4.jsonl",
    "data/eval/synonym_dev5.jsonl",
)
# Ontology schema names (kind "config_key", label "patch_config"), not synonym
# material: the held-out word "config" is only present as part of these.
SCHEMA_TOKENS = frozenset({"config"})
_TOKEN = re.compile(r"[A-Za-z][A-Za-z0-9\-]+")


def _heldout() -> set[str]:
    return {fold_token(w) for w in load_split()["heldout_words"]}


def _text_of(path: Path) -> str:
    raw = path.read_text(encoding="utf-8")
    if path.suffix == ".json":
        parts: list[str] = []

        def walk(o: object) -> None:
            if isinstance(o, dict):
                for k, v in o.items():
                    if k != "meta":
                        walk(v)
            elif isinstance(o, list):
                for v in o:
                    walk(v)
            elif isinstance(o, str):
                parts.append(o)

        walk(json.loads(raw))
        return "\n".join(parts)
    return raw


def audit(paths: tuple[str, ...] = HAND_WRITTEN, root: Path = ROOT) -> dict[str, list[str]]:
    """Map resource path -> sorted held-out words found in it."""
    held = _heldout()
    out: dict[str, list[str]] = {}
    for rel in paths:
        toks = {fold_token(t) for t in _TOKEN.findall(_text_of(root / rel))}
        out[rel] = sorted((toks & held) - SCHEMA_TOKENS)
    return out


# External snapshots built by querying a live service: held-out words may
# appear in the *answers* (the service was not written for this eval), but the
# *queries* must be exactly the corpus vocabulary, so no eval word chose what
# was fetched. Path -> meta key holding the query list.
QUERIED_EXTERNAL = {"data/datamuse/ml_neighbours.json.gz": "queried_words"}


def query_problems(paths: dict[str, str] | None = None, root: Path = ROOT) -> dict[str, dict[str, list[str]]]:
    """Map snapshot path -> queries that are not corpus words / corpus words not queried."""
    import gzip

    from ops_copilot.corpus import Corpus
    from ops_copilot.word_vectors import corpus_words

    vocab = set(corpus_words(f"{c.title} {c.text}" for c in Corpus().chunks))
    out: dict[str, dict[str, list[str]]] = {}
    for rel, key in (QUERIED_EXTERNAL if paths is None else paths).items():
        with gzip.open(root / rel, "rt", encoding="utf-8") as fh:
            queried = set(json.load(fh)["meta"].get(key) or ())
        out[rel] = {
            "not_corpus_words": sorted(queried - vocab),
            "missing_corpus_words": sorted(vocab - queried),
        }
    return out
