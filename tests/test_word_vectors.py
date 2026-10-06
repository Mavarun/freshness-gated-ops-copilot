"""Counter-fitted neighbour table: builder, loader and backoff contract."""

from __future__ import annotations

import gzip
import json

import numpy as np
import pytest

from ops_copilot.word_vectors import (
    NeighbourTable,
    WordVectorBackoff,
    build_neighbour_table,
    corpus_words,
    dump_table,
    read_text_vectors,
    words_fingerprint,
)

LINES = [
    "begin 1.0 0.1 0.0",
    "start 0.98 0.12 0.0",
    "starts 0.95 0.15 0.05",
    "goal 0.0 1.0 0.0",
    "target 0.05 0.99 0.0",
    "off 0.0 0.0 1.0",
    "on 0.0 0.2 -1.0",
    "banana -1.0 0.0 0.0",
]
CORPUS = ["Start the checkout-api deploy. The target is p99 under 300 ms.", "Turn it off."]


@pytest.fixture()
def toy():
    words, mat = read_text_vectors(LINES)
    targets = corpus_words(CORPUS)
    return words, mat, targets


def test_read_text_vectors_normalises(toy) -> None:
    words, mat, _ = toy
    assert words[0] == "begin" and mat.shape == (8, 3)
    assert np.allclose(np.linalg.norm(mat, axis=1), 1.0)


def test_corpus_words_are_plain_content_words() -> None:
    words = corpus_words(CORPUS)
    assert "start" in words and "target" in words and "off" in words
    assert "checkout-api" not in words and "p99" not in words and "300" not in words
    assert "the" not in words  # stopword


def test_table_maps_only_onto_targets_above_floor(toy) -> None:
    words, mat, targets = toy
    table = build_neighbour_table(words, mat, targets, floor=0.5, top_k=3)
    assert table["begin"][0][0] == "start" and table["begin"][0][1] > 0.99
    assert table["goal"][0][0] == "target"
    # never its own neighbour, never a non-target ("starts" is not a corpus word)
    assert all(w != "start" for w, _ in table["start"]) if "start" in table else True
    assert all(w in targets for rows in table.values() for w, _ in rows)
    # antonym-separated and unrelated words get nothing above the floor
    assert "banana" not in table
    assert all(w != "off" for w, _ in table.get("on", []))


def test_table_is_byte_stable(tmp_path, toy) -> None:
    words, mat, targets = toy
    table = build_neighbour_table(words, mat, targets, floor=0.5)
    meta = {"floor": 0.5, "corpus_fingerprint": words_fingerprint(targets)}
    a, b = tmp_path / "a.json.gz", tmp_path / "b.json.gz"
    dump_table(table, meta, a)
    dump_table(dict(reversed(list(table.items()))), meta, b)
    assert a.read_bytes() == b.read_bytes()
    raw = json.loads(gzip.decompress(a.read_bytes()))
    assert raw["meta"]["floor"] == 0.5
    loaded = NeighbourTable.load(a)
    assert loaded.get("begin")[0][0] == "start"


def _backoff(toy, tmp_path, **kw) -> WordVectorBackoff:
    words, mat, targets = toy
    path = tmp_path / "t.json.gz"
    dump_table(build_neighbour_table(words, mat, targets, floor=0.5), {"floor": 0.5}, path)
    return WordVectorBackoff(CORPUS, table=NeighbourTable.load(path), **kw)


def test_backoff_threshold_and_count(toy, tmp_path) -> None:
    bo = _backoff(toy, tmp_path, min_similarity=0.9, max_neighbours=1)
    assert [n.word for n in bo.neighbours("begin")] == ["start"]
    assert bo.neighbours("begin")[0].source == "wordvec"
    strict = _backoff(toy, tmp_path, min_similarity=0.9999, max_neighbours=1)
    assert strict.neighbours("begin") == ()


def test_backoff_never_looks_up_identifiers_or_numbers(toy, tmp_path) -> None:
    bo = _backoff(toy, tmp_path, min_similarity=0.5)
    for tok in ("checkout-api", "p99", "300", "ok"):
        assert bo.neighbours(tok) == ()


def test_backoff_folds_plurals(toy, tmp_path) -> None:
    bo = _backoff(toy, tmp_path, min_similarity=0.9)
    assert [n.word for n in bo.neighbours("goals")] == ["target"]


def test_threshold_below_table_floor_is_rejected(toy, tmp_path) -> None:
    with pytest.raises(ValueError):
        _backoff(toy, tmp_path, min_similarity=0.3)
