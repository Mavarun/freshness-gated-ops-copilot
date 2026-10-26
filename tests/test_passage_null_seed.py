"""The null-control sample seed is a config knob; the shipped value reproduces every artifact."""

from dataclasses import replace

from ops_copilot.config import CopilotConfig
from ops_copilot.passage_support import NULL_SEED
from ops_copilot.pipeline import Copilot


def _controls(seed=None):
    cfg = CopilotConfig() if seed is None else replace(CopilotConfig(), passage_support_null_seed=seed)
    return Copilot(config=cfg).grounder.passage_null_controls


def test_shipped_seed_is_the_recorded_one():
    assert CopilotConfig().passage_support_null_seed == NULL_SEED == 42
    assert _controls() == _controls(42)


def test_another_seed_draws_another_sample_of_the_same_size_from_the_same_pool():
    a, b = _controls(42), _controls(7)
    assert len(a) == len(b) == CopilotConfig().passage_support_null_controls
    assert a != b and len(set(a) & set(b)) < len(a)
    bot = Copilot(config=CopilotConfig())
    corpus = set(bot.grounder.idf)
    assert not (set(b) & corpus)


def test_the_seed_does_not_change_a_query_the_null_test_never_sees():
    q = "What is the current checkout p99 latency?"
    d = {s: Copilot(config=replace(CopilotConfig(), passage_support_null_seed=s)).ask(q).decision.value
         for s in (42, 7)}
    assert d == {42: "ANSWER", 7: "ANSWER"}
