"""Committed WordNet neighbour table: provenance, corpus binding, no eval filtering."""

import gzip
import json

from ops_copilot.corpus import Corpus
from ops_copilot.synonym_split import load_split
from ops_copilot.word_vectors import corpus_words, words_fingerprint
from ops_copilot.wordnet_senses import DEFAULT_TABLE, SOURCE_SHA256, load_table


def test_table_records_source_and_license():
    meta = load_table().meta
    assert meta["source_sha256"] == SOURCE_SHA256
    assert "WordNet 3.0" in meta["source_license"]
    assert meta["n_synsets"] == 82115


def test_table_is_bound_to_the_current_corpus():
    targets = corpus_words(f"{c.title} {c.text}" for c in Corpus().chunks)
    meta = load_table().meta
    assert meta["corpus_fingerprint"] == words_fingerprint(targets), (
        "corpus changed: rerun make wordnet-table"
    )


def test_every_target_is_a_corpus_word_and_rows_are_sorted():
    t = load_table()
    corpus = set(t.meta["corpus_words"])
    for key, rows in t.neighbours.items():
        assert rows, key
        assert all(r[0] in corpus and r[0] != key for r in rows)
        order = [(r[2], r[3], r[4], r[0]) for r in rows]
        assert order == sorted(order)


def test_table_is_not_filtered_by_eval_words():
    """Held-out words are keys exactly when WordNet relates them to a corpus word.

    The build never reads the split; this pins that the table did not drop or
    add eval words: it has thousands of keys unrelated to the eval.
    """
    t = load_table()
    split = load_split()
    eval_words = set(split["dev_words"]) | set(split["heldout_words"])
    keys = set(t.neighbours)
    assert len(keys - eval_words) > 10_000
    assert t.meta["n_entries"] == len(keys)


def test_committed_file_is_canonical_json():
    raw = json.loads(gzip.decompress(DEFAULT_TABLE.read_bytes()))
    assert set(raw) == {"meta", "neighbours"}
    assert list(raw["neighbours"]) == sorted(raw["neighbours"])
