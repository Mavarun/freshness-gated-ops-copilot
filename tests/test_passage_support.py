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


def _length_pairs():
    pairs = []
    for i in range(12):
        n = 4 if i % 2 else 40  # alternate short and long answers
        pairs.append({"site": "s", "qid": i, "aid": 100 + i, "q": ["disk", "full"], "a": ["disk", "full", *[f"w{i}_{j}" for j in range(n)]]})
    return pairs


def test_length_matched_hard_negatives_stay_near_the_own_answer_length() -> None:
    pairs = _length_pairs()

    def within_band(mining: str) -> list[bool]:
        rows = ps.build_training_pairs(pairs, {}, seed=5, mining=mining)
        owns = [len(r[1]) for r in rows if r[3] == "own"]
        hards = [len(r[1]) for r in rows if r[3] == "hard"]
        return [o / ps.LEN_BAND <= h <= o * ps.LEN_BAND for o, h in zip(owns, hards)]

    assert not all(within_band("max_lex"))  # coverage favours the long answers
    assert all(within_band("length_matched"))
    # same RNG stream by default: the PR #19 triples are reproduced exactly
    assert ps.build_training_pairs(pairs, {}, seed=5) == ps.build_training_pairs(pairs, {}, seed=5, mining="max_lex", n_random=1)


def test_extra_random_negatives_and_argument_checks() -> None:
    rows = ps.build_training_pairs(_length_pairs(), {}, seed=5, n_random=3)
    assert len(rows) == 12 * 5 and [r[3] for r in rows[:5]] == ["own", "hard", "random", "random", "random"]
    for bad in ({"mining": "longest"}, {"n_random": 0}, {"band": 0.5}):
        with pytest.raises(ValueError):
            ps.build_training_pairs(_length_pairs(), {}, **bad)


def test_length_profile_and_evaluate_report_both_hard_negative_kinds() -> None:
    rows = ps.build_training_pairs(_length_pairs(), {}, seed=5)
    prof = ps.length_profile(rows)
    assert set(prof) == {"own", "hard", "random"} and prof["own"]["n"] == 12
    assert prof["hard"]["median"] >= prof["own"]["median"]
    pairs = _length_pairs() + [
        {"site": "s", "qid": 50 + i, "aid": 500 + i, "q": ["cpu", f"k{i}"], "a": ["cpu", f"k{i}", "load"]} for i in range(60)
    ]
    ev = ps.evaluate(pairs, {"lexical coverage only": None}, {}, default_vectors())
    a = ev["auc"]["lexical coverage only"]
    assert {"vs_hard", "vs_hard_len", "vs_random"} <= set(a)
    assert set(ev["passage_length"]) == {"max_lex", "length_matched"}


def test_out_of_sample_numbers_are_pinned() -> None:
    ev = json.loads(EVAL.read_text())["eval"]
    auc, nos = ev["auc"], ev["rank_no_shared_word"]
    assert ev["n_test_questions"] > 2000
    # richer lexical features alone already beat raw coverage on hard negatives;
    # domain-vector features still add a further lift, and are what move the
    # no-shared-word ranking off chance.
    assert auc["classifier, no vectors"]["vs_hard"] > auc["lexical coverage only"]["vs_hard"] + 0.05
    assert auc["classifier"]["vs_hard"] > auc["classifier, no vectors"]["vs_hard"]
    assert auc["classifier"]["vs_hard"] > auc["lexical coverage only"]["vs_hard"] + 0.10
    assert nos["lexical coverage only"]["p_at_1"] == 0.0 and nos["classifier"]["p_at_1"] > 0.10
    # Oct 13: length-matched hard negatives + 3 random ones (chosen on validation)
    # fix the PR #19 ranking regression; the cost is a little hard-negative AUC
    # and no-shared-word P@1, pinned so it cannot grow silently.
    rank = ev["rank"]
    assert rank["classifier"]["p_at_1"] > rank["classifier, PR #19 recipe"]["p_at_1"] + 0.10
    assert rank["classifier"]["p_at_1"] > rank["lexical coverage only"]["p_at_1"]
    assert auc["classifier"]["vs_hard_len"] > auc["classifier, PR #19 recipe"]["vs_hard_len"] - 0.01
    assert nos["classifier"]["p_at_1"] > nos["classifier, PR #19 recipe"]["p_at_1"] - 0.03
    assert json.loads(EVAL.read_text())["meta"]["recipe"]["name"] == "length_matched/r3/b1.5"
    assert len(json.loads((ROOT / "data" / "domainvec" / "passage_support.json").read_text())["classifier"]["features"]) == len(
        __import__("ops_copilot.passage_support", fromlist=["FEATURES"]).FEATURES
    )
