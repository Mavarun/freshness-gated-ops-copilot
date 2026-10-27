"""Seed-free null test: the closed-form pool percentile equals the per-control loop."""

import numpy as np
import pytest

from ops_copilot.corpus import Corpus
from ops_copilot.passage_support import (
    NULL_TIE_EPS,
    PassageSupportModel,
    control_pool,
    control_words,
    null_percentile,
    pool_null_percentile,
    substitution_probs,
)
from ops_copilot.qa_translation import words as qa_words


@pytest.fixture(scope="module")
def setup():
    model = PassageSupportModel.load()
    chunks = Corpus().chunks
    texts = [f"{c.title} {c.text}" for c in chunks]
    corpus = {w for t in texts for w in qa_words(t)}
    pool = control_pool(model.vectors, corpus)
    passage = qa_words(next(c.text for c in chunks if "error budget" in c.text.lower()))
    return model, pool, passage, corpus


def _loop(model, q, word, p, weight, controls):
    out = []
    for c in controls:
        v = model.verdict([c if w == word else w for w in q], p, weight)
        out.append(np.nan if v is None else v.prob)
    return np.array(out)


QUERIES = [
    (["what", "flavour", "checkout", "error", "budget"], "flavour"),
    (["what", "checkout", "error", "budget", "flavour"], "flavour"),
    (["how", "spicy", "checkout", "error", "budget"], "spicy"),
    (["what", "lateness", "budget", "budget"], "lateness"),  # duplicate query word
]


def test_pool_is_the_sorted_unsampled_superset_of_every_seeded_sample(setup):
    model, pool, _, corpus = setup
    assert list(pool) == sorted(pool) and len(pool) == len(set(pool)) > 4000
    assert not set(pool) & corpus
    for seed in (1, 7, 42):
        assert set(control_words(model.vectors, corpus, k=100, seed=seed)) <= set(pool)


@pytest.mark.parametrize("q,word", QUERIES)
def test_closed_form_matches_the_loop_on_every_sampled_control(setup, q, word):
    model, pool, passage, _ = setup
    weight = lambda w: 1.0 + len(w) / 10  # noqa: E731  (non-uniform, so weights matter)
    ctrl = pool[::17]
    fast = substitution_probs(model, q, word, passage, weight, ctrl)
    slow = _loop(model, q, word, passage, weight, ctrl)
    assert np.allclose(fast, slow, atol=1e-6, equal_nan=True)


def test_fallback_controls_already_in_the_query_or_passage_use_the_loop(setup):
    model, _, passage, _ = setup
    q, word = ["what", "flavour", "checkout", "error", "budget"], "flavour"
    weight = lambda w: 1.0  # noqa: E731
    ctrl = ["checkout", passage[0], "budget"]  # a query word, a passage word
    assert np.allclose(substitution_probs(model, q, word, passage, weight, ctrl),
                       _loop(model, q, word, passage, weight, ctrl), atol=1e-12)
    # a word that is not in the query: every control scores as the query itself
    same = substitution_probs(model, q, "absent", passage, weight, ["alpha", "beta"])
    assert same[0] == same[1] == pytest.approx(model.verdict(q, passage, weight).prob, abs=1e-12)


def test_pool_percentile_equals_the_loop_percentile_on_the_same_controls(setup):
    model, pool, passage, _ = setup
    weight = lambda w: 1.0  # noqa: E731
    for q, word in QUERIES[:3]:
        ctrl = pool[::5]
        loop = null_percentile(model, q, word, passage, weight, ctrl)
        fast = pool_null_percentile(model, q, word, passage, weight, ctrl)
        real = model.verdict(q, passage, weight).prob
        near = np.sum(np.abs(_loop(model, q, word, passage, weight, ctrl) - real) <= NULL_TIE_EPS)
        assert abs(loop - fast) <= near / len(ctrl)


def test_pool_percentile_has_no_seed_and_is_deterministic(setup):
    model, pool, passage, _ = setup
    q, word = QUERIES[0]
    a = pool_null_percentile(model, q, word, passage, lambda w: 1.0, pool)
    assert a == pool_null_percentile(model, q, word, passage, lambda w: 1.0, tuple(reversed(pool)))
    assert 0.0 <= a <= 1.0
    assert pool_null_percentile(model, q, word, passage, lambda w: 1.0, ()) == 0.0
