"""Provenance of the committed counter-fitted neighbour table."""

from __future__ import annotations

from ops_copilot import Copilot
from ops_copilot.word_vectors import (
    DEFAULT_TABLE,
    SOURCE_N_WORDS,
    SOURCE_SHA256,
    NeighbourTable,
    corpus_words,
    words_fingerprint,
)


def _table() -> NeighbourTable:
    return NeighbourTable.load(DEFAULT_TABLE)


def test_table_comes_from_the_pinned_external_archive() -> None:
    meta = _table().meta
    assert meta["source_sha256"] == SOURCE_SHA256
    assert meta["n_source_words"] == SOURCE_N_WORDS
    assert meta["source_license"] == "Apache-2.0"
    assert meta["dim"] == 300


def test_table_matches_the_current_corpus(copilot: Copilot) -> None:
    """A corpus edit without ``scripts/build_word_neighbours.py`` fails here."""
    meta = _table().meta
    words = corpus_words(f"{c.title} {c.text}" for c in copilot.corpus.chunks)
    assert meta["corpus_words"] == words
    assert meta["corpus_fingerprint"] == words_fingerprint(words)


def test_table_rows_are_well_formed() -> None:
    table = _table()
    meta = table.meta
    targets = set(meta["corpus_words"])
    assert len(table.neighbours) == meta["n_entries"] > 5000
    for word, rows in table.neighbours.items():
        assert 1 <= len(rows) <= meta["top_k"]
        sims = [s for _, s in rows]
        assert sims == sorted(sims, reverse=True)
        assert all(meta["floor"] <= s <= 1.0001 for s in sims)
        assert all(t in targets and t != word for t, _ in rows)


def test_ops_jargon_is_unreachable_and_reported() -> None:
    """General-English vectors miss ops jargon; the table says which corpus words."""
    missing = set(_table().meta["corpus_words_not_in_source"])
    assert {"latency", "rollback", "runbook", "config", "credential"} <= missing
