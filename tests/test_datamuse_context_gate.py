"""Datamuse corpus-context gate: co-occurrence filter and re-rank (synthetic + pipeline)."""

import pytest

from ops_copilot.config import CopilotConfig
from ops_copilot.datamuse_senses import DatamuseSense, DatamuseTable
from ops_copilot.pipeline import Copilot

TABLE = DatamuseTable(
    meta={"corpus_words": ["latency", "wait", "chart", "schedule", "checkout", "rotation", "vault"]},
    neighbours={
        # source order puts the noisy word first, as for delay -> wait
        "delay": (("wait", 3, False, "rev"), ("latency", 9, True, "rev")),
        "plan": (("chart", 4, True, "rev"), ("schedule", 12, True, "rev")),
    },
)
DOCS = (
    frozenset({"checkout", "latency", "p99"}),
    frozenset({"wait", "queue"}),
    frozenset({"vault", "rotation", "schedule"}),
    frozenset({"chart", "grafana"}),
)


def sense(**kw):
    kw.setdefault("max_rank", 20)
    return DatamuseSense(table=TABLE, doc_words=DOCS, **kw)


def words(s, token):
    return [n.word for n in s.neighbours(token)]


def test_off_keeps_source_rank_order():
    s = sense(context_min=0)
    assert words(s, "delay") == ["wait"]
    assert words(s, "plan") == ["chart"]


def test_gate_keeps_only_words_sharing_a_chunk_with_the_query():
    s = sense(context_min=1)
    s.set_context(frozenset({"checkout"}))
    assert words(s, "delay") == ["latency"]  # wait never co-occurs with checkout
    s.set_context(frozenset({"vault", "rotation"}))
    assert words(s, "plan") == ["schedule"]  # chart blocked, the rank-12 word wins
    assert s.context_support("schedule", "plan") == 2


def test_higher_threshold_and_rank_cut_still_apply():
    s = sense(context_min=2)
    s.set_context(frozenset({"vault"}))
    assert words(s, "plan") == []
    s2 = sense(context_min=1, max_rank=10)
    s2.set_context(frozenset({"vault", "rotation"}))
    assert words(s2, "plan") == []  # schedule is rank 12


def test_query_token_and_candidate_do_not_count_as_context():
    s = sense(context_min=1)
    s.set_context(frozenset({"latency", "delay"}))
    assert words(s, "delay") == []


def test_no_context_means_no_mapping_and_cache_is_per_context():
    s = sense(context_min=1)
    assert words(s, "delay") == []
    s.set_context(frozenset({"checkout"}))
    assert words(s, "delay") == ["latency"]
    s.set_context(frozenset({"queue"}))
    assert words(s, "delay") == ["wait"]


def test_gate_needs_doc_words_and_a_non_negative_threshold():
    with pytest.raises(ValueError):
        DatamuseSense(table=TABLE, context_min=1)
    with pytest.raises(ValueError):
        DatamuseSense(table=TABLE, doc_words=DOCS, context_min=-1)


def test_default_config_is_off_and_pipeline_builds_chunk_words_only_when_on():
    assert CopilotConfig().datamuse_context_min == 0
    off = Copilot(config=CopilotConfig(use_datamuse_ml=True, datamuse_scope="lone"))
    assert off.datamuse.doc_words is None
    on = Copilot(config=CopilotConfig(use_datamuse_ml=True, datamuse_scope="lone", datamuse_context_min=1))
    assert on.datamuse.doc_words is not None
    assert len(on.datamuse.doc_words) == len(on.corpus.chunks)


def test_grounder_sets_the_query_context_and_clears_it():
    bot = Copilot(config=CopilotConfig(use_datamuse_ml=True, datamuse_scope="lone", datamuse_context_min=1,
                                       datamuse_max_rank=20))
    seen = []
    orig = bot.datamuse.neighbours

    def spy(tok):
        seen.append(bot.datamuse.context)
        return orig(tok)

    bot.datamuse.neighbours = spy
    bot.grounder.terms("What is the current checkout p99 delay?")
    assert seen and all(c is not None and "checkout" in c for c in seen)
    assert "delay" not in seen[0]  # only corpus words of the query
    assert bot.datamuse.context is None
