"""Passage-level answer-support classifier: features, committed model, OOS numbers."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

from ops_copilot import passage_support as ps
from ops_copilot.domain_vectors import default_vectors
from ops_copilot.qa_translation import load_table as load_qa_table

ROOT = Path(__file__).resolve().parents[1]
EVAL = ROOT / "artifacts" / "passage_support_eval.json"


@pytest.fixture(scope="module")
def model():
    return ps.PassageSupportModel.load()


def _w(_: str) -> float:
    return 1.0


def test_features_on_a_toy_pair() -> None:
    dv = default_vectors()
    f = ps.pair_features(["disk", "full"], ["disk", "full", "space"], _w, dv)
    assert f["lex"] == 1.0 and f["soft"] == 1.0 and f["missing"] == 0.0 and f["weakest"] == 1.0
    g = ps.pair_features(["disk", "full"], ["drive", "full"], _w, dv)
    assert g["lex"] == 0.5 and g["missing"] == 0.5
    assert g["best"]["disk"][0] == "drive" and 0.5 < g["weakest"] < 1.0
    assert 0.5 < g["soft"] < 1.0
    assert ps.pair_features([], ["disk"], _w, dv) is None


def test_unknown_words_get_no_credit() -> None:
    f = ps.pair_features(["zzqx"], ["disk"], _w, default_vectors())
    assert f["soft"] == 0.0 and f["best"]["zzqx"] == (None, 0.0) and f["centroid"] == 0.0


def test_committed_model_matches_the_feature_list(model) -> None:
    c = model.classifier
    assert c.names == ps.FEATURES
    assert c.mean.shape == c.scale.shape == c.coef.shape == (len(ps.FEATURES),)
    assert np.all(c.scale > 0)
    assert model.meta["raw_sha256"] == load_qa_table()["meta"]["raw_sha256"]
    assert "CC BY-SA 4.0" in model.meta["license"]


def test_full_coverage_scores_above_a_related_miss(model) -> None:
    dv = default_vectors()
    full = model.verdict(["disk", "full"], ["disk", "full", "space"], _w)
    near = model.verdict(["disk", "full"], ["drive", "full", "space"], _w)
    far = model.verdict(["disk", "full"], ["firewall", "nat", "outbound"], _w)
    assert full.prob > near.prob > far.prob
    assert near.best["disk"][0] == "drive"
    assert model.verdict([], ["disk"], _w) is None
    assert dv is model.vectors


def test_hard_negative_shares_more_words_than_random() -> None:
    pairs = []
    for i in range(12):
        pairs.append({"site": "s", "qid": i, "aid": 100 + i, "q": ["disk", f"x{i}"], "a": ["disk", f"y{i}"] if i % 2 else [f"z{i}"]})
    rows = ps.build_training_pairs(pairs, {}, seed=3)
    assert [k for *_, k in rows[:3]] == ["own", "hard", "random"]
    assert sum(y for _, _, y, _ in rows) == 12 and len(rows) == 36
    assert rows == ps.build_training_pairs(pairs, {}, seed=3)  # seeded


def test_out_of_sample_numbers_are_pinned() -> None:
    ev = json.loads(EVAL.read_text())["eval"]
    auc, nos = ev["auc"], ev["rank_no_shared_word"]
    assert ev["n_test_questions"] > 2000
    # the vectors are what helps: lexical-only classifier does not beat coverage on hard negatives by much
    assert auc["classifier"]["vs_hard"] > auc["classifier, no vectors"]["vs_hard"] + 0.05
    assert auc["classifier"]["vs_hard"] > auc["lexical coverage only"]["vs_hard"] + 0.05
    assert nos["lexical coverage only"]["p_at_1"] == 0.0 and nos["classifier"]["p_at_1"] > 0.05
