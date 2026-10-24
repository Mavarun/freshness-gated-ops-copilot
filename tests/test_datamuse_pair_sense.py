"""Counter-fitted cosine per Datamuse pair: build, alignment, provenance and size."""

from __future__ import annotations

import gzip
import json

import numpy as np
import pytest

from ops_copilot.datamuse_pair_sense import (
    DEFAULT_TABLE,
    PairSenseTable,
    build_pair_table,
    dump_table,
    load_pair_table,
)
from ops_copilot.datamuse_senses import DatamuseTable, load_table
from ops_copilot.word_vectors import SOURCE_SHA256


def _unit(rows):
    m = np.asarray(rows, dtype=np.float32)
    return m / np.linalg.norm(m, axis=1, keepdims=True)


def test_build_scores_only_existing_pairs_and_marks_oov_as_none():
    nb = {"delay": [["latency", 3, 1, "rev"], ["wait", 1, 0, "rev"]], "zzz": [["latency", 9, 0, "rev"]]}
    words = ["delay", "latency", "wait"]
    vecs = _unit([[1, 0], [0.8, 0.6], [0, 1]])
    table = build_pair_table(nb, words, vecs)
    assert table == {"delay": [80, 0], "zzz": [None]}


def test_dump_is_byte_stable_and_load_aligns_with_datamuse_rows(tmp_path):
    dm = DatamuseTable(meta={}, neighbours={"delay": (("latency", 3, True, "rev"), ("wait", 1, False, "rev"))})
    table = {"delay": [80, None]}
    a, b = tmp_path / "a.gz", tmp_path / "b.gz"
    dump_table(table, {"x": 1}, a)
    dump_table(table, {"x": 1}, b)
    assert a.read_bytes() == b.read_bytes()
    t = PairSenseTable.load(a, datamuse=dm)
    assert t.cosine("delay", "latency") == 0.8 and t.cosine("Delay", "wait") is None
    assert t.cosine("delay", "nowhere") is None and t.cosine("unknown", "latency") is None


def test_load_rejects_a_table_out_of_step_with_the_datamuse_snapshot(tmp_path):
    dm = DatamuseTable(meta={}, neighbours={"delay": (("latency", 3, True, "rev"),)})
    p = tmp_path / "t.gz"
    dump_table({"delay": [80, 10]}, {}, p)
    with pytest.raises(ValueError):
        PairSenseTable.load(p, datamuse=dm)


def test_committed_table_covers_every_datamuse_pair_and_pins_its_sources():
    raw = json.loads(gzip.decompress(DEFAULT_TABLE.read_bytes()))
    dm = load_table()
    meta = raw["meta"]
    assert meta["source_sha256"] == SOURCE_SHA256
    assert meta["datamuse_raw_sha256"] == dm.meta["raw_sha256"]
    assert meta["datamuse_corpus_fingerprint"] == dm.meta["corpus_fingerprint"]
    assert set(raw["cosine"]) == set(dm.neighbours)
    assert meta["n_pairs"] == sum(len(v) for v in dm.neighbours.values()) == 39847
    assert meta["n_missing"] == 10685
    assert all(v is None or -100 <= v <= 100 for vals in raw["cosine"].values() for v in vals)
    assert DEFAULT_TABLE.stat().st_size < 512 * 1024


def test_substitutability_is_not_collocation_on_the_pr27_trap():
    t = load_pair_table()
    # legal is 21st in Datamuse's list for duty ("legal duty"); the vectors disagree.
    assert t.cosine("legal", "duty") == 0.26
    assert t.cosine("itinerary", "path") == 0.77 and t.cosine("itinerary", "schedule") == 0.21
