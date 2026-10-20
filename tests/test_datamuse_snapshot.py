"""Committed Datamuse snapshot: provenance, corpus-only queries, no eval input."""

import re
from pathlib import Path

from ops_copilot.corpus import Corpus
from ops_copilot.datamuse_senses import DEFAULT_TABLE, load_table
from ops_copilot.word_vectors import corpus_words, words_fingerprint

ROOT = Path(__file__).resolve().parents[1]


def _corpus():
    return corpus_words(f"{c.title} {c.text}" for c in Corpus().chunks)


def test_snapshot_pins_its_source():
    m = load_table().meta
    assert m["fetched_on"] == "2026-10-20"
    assert re.fullmatch(r"[0-9a-f]{64}", m["raw_sha256"])
    assert "datamuse" in m["source_url"] and "ml=" in m["source_url"]
    assert m["max_results"] == 100
    assert DEFAULT_TABLE.stat().st_size < 400_000


def test_queries_were_exactly_the_corpus_words():
    m = load_table().meta
    words = _corpus()
    assert m["queried_words"] == words
    assert m["corpus_fingerprint"] == words_fingerprint(words)


def test_every_row_targets_a_corpus_word_and_never_itself():
    t = load_table()
    vocab = set(t.meta["corpus_words"])
    for key, rows in t.neighbours.items():
        assert rows, key
        for word, rank, _noun, d in rows:
            assert word in vocab and word != key
            assert 1 <= rank <= t.meta["max_results"]
            assert d in ("rev", "fwd")
        assert [r[1] for r in rows] == sorted(r[1] for r in rows)


def test_fetch_and_build_scripts_read_no_eval_file():
    for name in ("fetch_datamuse_ml.py", "build_datamuse_neighbours.py"):
        src = (ROOT / "scripts" / name).read_text()
        for banned in ("data/eval", "golden", "synonym_split", "synonym_dev2", "paraphrase", "heldout"):
            assert banned not in src, (name, banned)
    src = (ROOT / "src" / "ops_copilot" / "datamuse_senses.py").read_text()
    assert "synonym_split" not in src and "synonym_dev2" not in src


def test_usage_synonyms_wordnet_lacks_are_present():
    # corpus-side check (no eval row read): Datamuse ranks delay highly for latency
    t = load_table()
    assert any(w == "latency" and r <= 20 for w, r, _n, _d in t.neighbours["delay"])
