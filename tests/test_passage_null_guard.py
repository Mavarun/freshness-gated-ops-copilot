from dataclasses import replace

import numpy as np
import pytest

from ops_copilot.config import CopilotConfig
from ops_copilot.domain_vectors import default_vectors
from ops_copilot.passage_support import control_words, null_percentile
from ops_copilot.pipeline import Copilot


class _Verdict:
    def __init__(self, prob):
        self.prob = prob


class _ToyModel:
    """P = 0.9 if the query holds 'good', 0.5 if it holds 'meh', else 0.1."""

    def verdict(self, q, p, weight):
        if "good" in q:
            return _Verdict(0.9)
        return _Verdict(0.5 if "meh" in q else 0.1)


def test_control_words_are_seeded_sorted_pool_samples_outside_exclude():
    dv = default_vectors()
    a = control_words(dv, {"checkout"}, k=50)
    assert a == control_words(dv, {"checkout"}, k=50)
    assert len(a) == len(set(a)) == 50
    assert all(w.isalpha() and len(w) >= 4 and w != "checkout" for w in a)
    assert control_words(dv, set(a[:10]), k=50) != a
    with pytest.raises(ValueError):
        control_words(dv, (), k=0)


def test_null_percentile_counts_controls_strictly_below_the_real_word():
    m = _ToyModel()
    assert null_percentile(m, ["what", "good"], "good", ["x"], lambda w: 1.0, ["a", "b", "meh"]) == 1.0
    # an unrelated word scores like the controls: nothing is below it
    assert null_percentile(m, ["what", "bad"], "bad", ["x"], lambda w: 1.0, ["a", "b"]) == 0.0
    assert null_percentile(m, ["what", "meh"], "meh", ["x"], lambda w: 1.0, ["a", "b", "meh", "good"]) == 0.5
    assert null_percentile(m, ["what", "good"], "good", ["x"], lambda w: 1.0, []) == 0.0


def test_off_by_default_and_controls_exclude_corpus_words():
    cfg = CopilotConfig()
    assert cfg.passage_support_null_min == 0.0
    assert Copilot(config=cfg).grounder.passage_null_controls == ()
    g = Copilot(config=replace(cfg, passage_support_null_min=0.3)).grounder
    assert len(g.passage_null_controls) == 100
    assert not set(g.passage_null_controls) & set(g.idf)


def test_guard_never_adds_a_rescue():
    """The test can only veto: every row it answers, the default answers too."""
    base = Copilot(config=CopilotConfig())
    on = Copilot(config=replace(CopilotConfig(), passage_support_null_min=0.5))
    for q in ("What is the production maintenance change span?", "What colour is the checkout_retry feature flag?",
              "What is the remaining error margin for checkout?"):
        a, b = base.ask(q), on.ask(q)
        if b.grounding and b.grounding.passage_rescued:
            assert a.grounding.passage_rescued == b.grounding.passage_rescued


def test_sticky_veto_is_off_by_default_and_remembers_vetoed_words_per_query():
    assert CopilotConfig().passage_support_null_sticky is False
    g = Copilot(config=replace(CopilotConfig(), passage_support_null_min=0.5, passage_support_null_sticky=True)).grounder
    g._remember_null_veto("q1", "flavour")
    g._remember_null_veto("q1", "weight")
    assert g._null_vetoed["q1"] == frozenset({"flavour", "weight"})
    for i in range(600):
        g._remember_null_veto(f"x{i}", "w")
    assert len(g._null_vetoed) == 512 and "q1" not in g._null_vetoed
