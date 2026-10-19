"""WordNet sense-frequency gate (synthetic table; no eval words)."""

import pytest

from ops_copilot.config import CopilotConfig
from ops_copilot.pipeline import Copilot
from ops_copilot.wordnet_senses import WordNetNounSense, WordNetTable

# Rows: (corpus_word, relation, path, fan_out, sense_rank)
TABLE = WordNetTable(
    meta={},
    neighbours={
        "widget": (
            ("gadget", "syn", 0, 0, 0),
            ("trinket", "syn", 0, 0, 2),
            ("device", "hyper", 1, 0, 1),
        ),
    },
)


def words(**kw):
    return [n.word for n in WordNetNounSense(max_path=1, max_neighbours=9, table=TABLE, **kw).neighbours("widget")]


def test_default_keeps_every_sense():
    assert words() == ["gadget", "trinket", "device"]


def test_first_sense_only():
    assert words(max_sense_rank=1) == ["gadget"]


def test_first_two_senses():
    assert words(max_sense_rank=2) == ["gadget", "device"]


def test_bad_rank_rejected():
    with pytest.raises(ValueError):
        WordNetNounSense(table=TABLE, max_sense_rank=0)


def test_config_zero_means_all_senses():
    assert CopilotConfig().wordnet_max_sense_rank == 0
    bot = Copilot(config=CopilotConfig(use_wordnet_noun_sense=True))
    assert bot.wordnet_noun.max_sense_rank is None
    bot = Copilot(config=CopilotConfig(use_wordnet_noun_sense=True, wordnet_max_sense_rank=2))
    assert bot.wordnet_noun.max_sense_rank == 2
