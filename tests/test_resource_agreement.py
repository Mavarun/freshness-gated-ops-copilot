import pytest

from ops_copilot.resource_agreement import SOURCES, AgreementSense


def _fake(table):
    return {name: (lambda t, name=name: frozenset(table.get(name, {}).get(t, ()))) for name in SOURCES}


TABLE = {
    "wordvec": {"usage": {"utilization", "use"}, "glorp": {"latency"}, "lag": {"latency"}},
    "datamuse": {"usage": {"utilization"}, "glorp": {"checkout"}},
    "wordnet": {"usage": {"utilization", "use"}},
    "wiktionary": {},
    "tagsyn": {"glorp": {"latency"}},
}
WORDS = frozenset({"utilization", "use", "latency", "checkout", "usage"})


def sense(**kw):
    return AgreementSense(WORDS, _fake(TABLE), **kw)


def test_votes_count_resources_per_candidate():
    v = sense(scope="all").votes("usage")
    assert v["utilization"] == 3 and v["use"] == 2


def test_min_votes_filters_single_resource_candidates():
    s = sense(scope="all", min_votes=2)
    assert [n.word for n in s.neighbours("glorp")] == ["latency"]
    assert sense(scope="all", min_votes=3).neighbours("glorp") == ()


def test_highest_vote_first_and_cap():
    s = sense(scope="known", min_votes=2, max_neighbours=2)
    assert [n.word for n in s.neighbours("usage")] == ["utilization", "use"]
    assert [n.word for n in sense(min_votes=2).neighbours("usage")] == ["utilization"]


def test_known_scope_never_maps_unknown_words():
    assert sense(scope="known").neighbours("glorp") == ()


def test_lone_scope_respects_suspend():
    s = sense(scope="lone")
    assert s.lone_unknown
    s.set_suspend_unknown(True)
    assert s.neighbours("glorp") == ()
    s.set_suspend_unknown(False)
    assert [n.word for n in s.neighbours("glorp")] == ["latency"]


def test_one_vote_is_not_agreement():
    assert sense(scope="all", min_votes=2).neighbours("lag") == ()


def test_identifiers_and_short_tokens_are_never_looked_up():
    s = sense(scope="all", min_votes=1)
    assert s.neighbours("p99") == () and s.neighbours("db") == ()


def test_bad_arguments():
    with pytest.raises(ValueError):
        sense(scope="every")
    with pytest.raises(ValueError):
        sense(min_votes=6)
    with pytest.raises(ValueError):
        sense(min_votes=0)


def test_real_tables_load_and_propose_corpus_words_only():
    from ops_copilot.pipeline import Copilot

    bot = Copilot()
    texts = [f"{c.title} {c.text}" for c in bot.corpus.chunks]
    s = AgreementSense.from_corpus(texts, scope="all", min_votes=1, max_neighbours=50)
    got = s.neighbours("usage")
    assert got and all(n.word in s.corpus_words for n in got)
    # utilization is proposed by at least two resources for usage (a dev pair)
    assert s.votes("usage")["utilization"] >= 2
