"""WordNet noun sense in the pipeline: off by default, one shared noun slot."""

from ops_copilot.config import CopilotConfig
from ops_copilot.noun_gloss_sense import NounGlossSenseBackoff
from ops_copilot.pipeline import Copilot
from ops_copilot.wordnet_senses import ChainedNounSense, WordNetNounSense


def test_off_by_default():
    cfg = CopilotConfig()
    assert cfg.use_wordnet_noun_sense is False
    bot = Copilot(config=cfg)
    assert bot.wordnet_noun is None
    assert bot.noun_sense is None


def test_on_fills_the_noun_read_path_slot():
    bot = Copilot(config=CopilotConfig(use_wordnet_noun_sense=True))
    assert isinstance(bot.wordnet_noun, WordNetNounSense)
    assert bot.grounder.noun_gloss is bot.wordnet_noun
    assert bot.retriever.noun_gloss is bot.wordnet_noun
    assert bot.grounder.noun_gloss_known is True


def test_chain_prefers_wiktionary_gloss_then_wordnet():
    bot = Copilot(
        config=CopilotConfig(use_wordnet_noun_sense=True, use_noun_gloss_sense=True)
    )
    assert isinstance(bot.noun_sense, ChainedNounSense)
    assert isinstance(bot.noun_sense.parts[0], NounGlossSenseBackoff)
    assert bot.noun_sense.parts[1] is bot.wordnet_noun


def test_dev_usage_row_maps_to_utilization_and_tags_term_kind():
    bot = Copilot(config=CopilotConfig(use_wordnet_noun_sense=True))
    term = bot.grounder._term("usage")
    assert term is not None
    assert "utilization" in term.alts
