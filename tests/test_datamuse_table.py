"""Datamuse ml table: parsing, inversion and byte-stable dumps (synthetic responses)."""

import gzip
import json

import pytest

from ops_copilot.datamuse_senses import (
    DatamuseTable,
    build_neighbour_table,
    dump_table,
    parse_response,
)

RESP = {
    "latency": [
        {"word": "reaction time", "score": 900},
        {"word": "lag", "score": 800, "tags": ["n"]},
        {"word": "Delay", "score": 700},
        {"word": "delay", "score": 600, "tags": ["n", "v"]},
        {"word": "lag", "score": 500},
        {"word": "x2", "score": 400},
        {"word": "throughput", "score": 300, "tags": ["n"]},
    ],
    "throughput": [
        {"word": "capacity", "score": 9, "tags": ["n"]},
        {"word": "latency", "score": 8, "tags": ["n"]},
        {"word": "lag", "score": 7, "tags": ["v"]},
    ],
}
TARGETS = ["latency", "throughput"]


def test_parse_keeps_source_rank_and_plain_words_only():
    got = parse_response(RESP["latency"])
    # multi-word, capitalised, duplicate and non-alpha results are dropped, ranks kept
    assert got == [("lag", 2, True), ("delay", 4, True), ("throughput", 7, True)]


def test_inversion_maps_result_words_to_corpus_words():
    table = build_neighbour_table(RESP, TARGETS)
    # lag: rank 2 in latency's list, rank 3 in throughput's list
    assert table["lag"] == [["latency", 2, 1, "rev"], ["throughput", 3, 0, "rev"]]
    assert table["delay"] == [["latency", 4, 1, "rev"]]
    # corpus word -> corpus word in both directions, best rank kept
    # (latency is rank 2 for throughput; throughput is rank 7 for latency)
    assert table["latency"] == [["throughput", 2, 1, "rev"]]
    assert table["throughput"] == [["latency", 2, 1, "fwd"]]
    assert table["capacity"] == [["throughput", 1, 1, "rev"]]


def test_no_identity_rows():
    table = build_neighbour_table(RESP, TARGETS)
    for key, rows in table.items():
        assert all(r[0] != key for r in rows)


def test_response_for_a_non_corpus_word_is_rejected():
    with pytest.raises(ValueError):
        build_neighbour_table({"payroll": RESP["latency"]}, TARGETS)


def test_dump_is_byte_stable_and_round_trips(tmp_path):
    table = build_neighbour_table(RESP, TARGETS)
    a, b = tmp_path / "a.json.gz", tmp_path / "b.json.gz"
    dump_table(table, {"corpus_words": TARGETS}, a)
    dump_table(table, {"corpus_words": TARGETS}, b)
    assert a.read_bytes() == b.read_bytes()
    loaded = DatamuseTable.load(a)
    assert loaded.neighbours["lag"][0] == ("latency", 2, True, "rev")
    raw = json.loads(gzip.decompress(a.read_bytes()))
    assert raw["meta"]["corpus_words"] == TARGETS
