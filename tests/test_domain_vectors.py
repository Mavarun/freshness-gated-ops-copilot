"""Ops-domain PPMI-SVD word vectors (outside Stack Exchange data)."""

from __future__ import annotations

import gzip
import json
import re

import numpy as np
import pytest

from ops_copilot import domain_vectors as dvm
from ops_copilot.qa_translation import load_table as load_qa_table


@pytest.fixture(scope="module")
def dv():
    return dvm.default_vectors()


def test_table_shape_and_unit_rows(dv) -> None:
    assert len(dv.words) == dvm.VOCAB_SIZE
    assert dv.vectors.shape == (dvm.VOCAB_SIZE, dvm.DIM)
    assert np.allclose(np.linalg.norm(dv.vectors, axis=1), 1.0, atol=1e-5)


def test_words_only_no_post_text(dv) -> None:
    assert all(re.fullmatch(r"[a-z]{2,24}", w) for w in dv.words)
    raw = json.loads(gzip.decompress(dvm.DEFAULT_TABLE.read_bytes()))
    assert set(raw) == {"meta", "words", "dim", "int8_b64"}


def test_same_snapshot_as_the_qa_table_and_train_split_only(dv) -> None:
    assert dv.meta["raw_sha256"] == load_qa_table()["meta"]["raw_sha256"]
    assert "train questions only" in dv.meta["split"]
    for k, v in {"window": 4, "dim": 48, "cds_alpha": 0.75, "eig_p": 0.5, "svd_seed": 0}.items():
        assert dv.meta[k] == v


def test_similarity_and_best(dv) -> None:
    assert dv.similarity("disk", "disk") == pytest.approx(1.0, abs=1e-5)
    assert dv.similarity("disk", "notaword") is None
    word, sim = dv.best("disk", ["drive", "firewall", "notaword"])
    assert word == "drive" and sim > dv.similarity("disk", "firewall")
    assert dv.best("notaword", ["drive"]) == (None, 0.0)
    assert dv.best("disk", ["disk"]) == (None, 0.0)  # a word never vouches for itself


def test_neighbours_are_topical(dv) -> None:
    # sanity on words outside every eval file
    assert "drive" in {w for w, _ in dv.neighbours("disk", 5)}
    assert "postgresql" in {w for w, _ in dv.neighbours("mysql", 5)}


def test_train_docs_drop_test_questions_and_duplicates() -> None:
    from ops_copilot.qa_translation import is_test

    qids = [i for i in range(1, 400)]
    test_q = next(i for i in qids if is_test("serverfault", i))
    train_q = next(i for i in qids if not is_test("serverfault", i))
    docs = [
        {"site": "serverfault", "qid": test_q, "seqs": [["held"]]},
        {"site": "serverfault", "qid": train_q, "seqs": [["kept"], ["too"]]},
        {"site": "serverfault", "qid": train_q, "seqs": [["dup"]]},
    ]
    assert dvm.train_docs(docs) == [["kept"], ["too"]]


def test_training_is_deterministic_on_a_toy_corpus() -> None:
    rng = np.random.default_rng(0)
    vocab = [f"w{chr(97 + i)}x" for i in range(26)]
    seqs = [[vocab[j] for j in rng.integers(0, 26, 60)] for _ in range(400)]
    old = (dvm.MIN_COUNT, dvm.DIM)
    try:
        dvm.MIN_COUNT, dvm.DIM = 1, 8
        a = dvm.train_vectors(seqs)
        b = dvm.train_vectors(seqs)
    finally:
        dvm.MIN_COUNT, dvm.DIM = old
    assert a.words == b.words and np.array_equal(a.vectors, b.vectors)


def test_quantised_round_trip(tmp_path, dv) -> None:
    sub = dvm.DomainVectors(dv.words[:50], dv.vectors[:50], {"x": 1})
    p = tmp_path / "t.json.gz"
    sha1 = dvm.dump_table(sub, p)
    sha2 = dvm.dump_table(sub, p)
    assert sha1 == sha2  # byte-stable
    back = dvm.load_table(p)
    assert back.words == sub.words
    assert np.max(np.abs(back.vectors - sub.vectors)) < 0.03
