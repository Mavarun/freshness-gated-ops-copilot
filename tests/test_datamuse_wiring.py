"""Datamuse ml in the pipeline: off by default, chained after WordNet in the noun slot."""

import pytest

from ops_copilot.config import CopilotConfig
from ops_copilot.datamuse_senses import DatamuseSense
from ops_copilot.pipeline import Copilot
from ops_copilot.wordnet_senses import ChainedNounSense


def test_off_by_default_and_default_bot_unchanged():
    cfg = CopilotConfig()
    assert cfg.use_datamuse_ml is False
    bot = Copilot(config=cfg)
    assert bot.datamuse is None
    assert bot.noun_sense is None
    assert bot.retriever.noun_gloss is None


def test_known_scope_is_grounding_only():
    bot = Copilot(config=CopilotConfig(use_datamuse_ml=True))
    assert isinstance(bot.datamuse, DatamuseSense)
    assert bot.datamuse.known_only is True
    assert bot.grounder.noun_gloss is bot.datamuse
    assert bot.grounder.noun_gloss_known is True
    assert bot.retriever.noun_gloss is None
    # an unknown word is never mapped in known scope
    assert bot.datamuse.neighbours("delay") == ()
    assert bot.grounder._term("delay").kind == "unknown"


def test_all_scope_enters_the_retrieval_rewrite_and_maps_unknown_words():
    bot = Copilot(config=CopilotConfig(use_datamuse_ml=True, datamuse_scope="all", datamuse_max_rank=20,
                                         datamuse_max_neighbours=2))
    assert bot.retriever.noun_gloss is bot.datamuse
    assert "latency" in {n.word for n in bot.datamuse.neighbours("delay")}
    assert bot.grounder._term("delay").kind == "datamuse_ml"


def test_lone_scope_maps_only_a_single_unknown_word():
    bot = Copilot(config=CopilotConfig(use_datamuse_ml=True, datamuse_scope="lone", datamuse_max_rank=20))
    assert bot.retriever.noun_gloss is None
    one = {t.token: t for t in bot.grounder.terms("What is the checkout delay?")}
    assert one["delay"].kind == "datamuse_ml"
    many = {t.token: t for t in bot.grounder.terms("What is the delay of the zzpayroll zzconnector?")}
    assert many["delay"].kind == "unknown"
    assert bot.datamuse.suspend_unknown is False


def test_chain_order_wordnet_before_datamuse():
    bot = Copilot(config=CopilotConfig(use_datamuse_ml=True, use_wordnet_noun_sense=True))
    assert isinstance(bot.noun_sense, ChainedNounSense)
    assert bot.noun_sense.parts == (bot.wordnet_noun, bot.datamuse)


def test_bad_scope_rejected():
    with pytest.raises(ValueError):
        Copilot(config=CopilotConfig(use_datamuse_ml=True, datamuse_scope="every"))


def test_wordnet_all_scope_rewrite_unchanged_when_datamuse_off():
    bot = Copilot(config=CopilotConfig(use_wordnet_noun_sense=True, wordnet_scope="all"))
    assert bot.retriever.noun_gloss is bot.wordnet_noun
