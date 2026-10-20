"""Datamuse ml gate: rank cut-off, noun tag, neighbour cap, scopes (synthetic table)."""

import pytest

from ops_copilot.datamuse_senses import DatamuseSense, DatamuseTable

TABLE = DatamuseTable(
    meta={"corpus_words": ["latency", "throughput", "capacity"]},
    neighbours={
        "lag": (("latency", 2, True, "rev"), ("throughput", 6, False, "rev")),
        "latency": (("throughput", 2, True, "rev"),),
        "slowness": (("latency", 30, True, "rev"),),
    },
)


def words(token="lag", **kw):
    return [n.word for n in DatamuseSense(table=TABLE, **kw).neighbours(token)]


def test_rank_cut_off():
    assert words(max_rank=1) == []
    assert words(max_rank=2) == ["latency"]
    assert words(max_rank=10, max_neighbours=5) == ["latency", "throughput"]
    assert words("slowness", max_rank=10) == []
    assert words("slowness", max_rank=50) == ["latency"]


def test_neighbour_cap_keeps_best_rank_first():
    assert words(max_rank=10, max_neighbours=1) == ["latency"]


def test_noun_only_drops_untagged_results():
    assert words(max_rank=10, max_neighbours=5, noun_only=True) == ["latency"]


def test_known_scope_never_maps_an_unknown_word():
    assert words(max_rank=10, known_only=True) == []
    assert words("latency", max_rank=10, known_only=True) == ["throughput"]


def test_suspend_unknown_blocks_unknown_words_only():
    s = DatamuseSense(table=TABLE, max_rank=10, lone_unknown=True)
    s.set_suspend_unknown(True)
    assert s.neighbours("lag") == ()
    assert [n.word for n in s.neighbours("latency")] == ["throughput"]
    s.set_suspend_unknown(False)
    assert [n.word for n in s.neighbours("lag")] == ["latency"]


def test_corpus_filter_and_non_lookupable_tokens():
    assert words(max_rank=10, max_neighbours=5, corpus_words=frozenset({"throughput"})) == ["throughput"]
    assert words("p99", max_rank=10) == []
    assert words("la", max_rank=10) == []


def test_score_is_inverse_rank_and_kind_is_tagged():
    (n,) = DatamuseSense(table=TABLE, max_rank=10).neighbours("lag")
    assert n.similarity == pytest.approx(0.5)
    assert n.source == "datamuse_ml"
    assert DatamuseSense.term_kind == "datamuse_ml"


def test_bad_gate_rejected():
    with pytest.raises(ValueError):
        DatamuseSense(table=TABLE, max_rank=0)
    with pytest.raises(ValueError):
        DatamuseSense(table=TABLE, max_neighbours=0)
