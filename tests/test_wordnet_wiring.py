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
    bot = Copilot(config=CopilotConfig(use_wordnet_noun_sense=True, wordnet_scope="all"))
    assert isinstance(bot.wordnet_noun, WordNetNounSense)
    assert bot.wordnet_noun.known_only is False
    assert bot.grounder.noun_gloss is bot.wordnet_noun
    assert bot.retriever.noun_gloss is bot.wordnet_noun
    assert bot.grounder.noun_gloss_known is True


def test_known_scope_is_grounding_only_and_skips_unknown_words():
    bot = Copilot(config=CopilotConfig(use_wordnet_noun_sense=True))
    assert bot.config.wordnet_scope == "known"
    assert bot.grounder.noun_gloss is bot.wordnet_noun
    assert bot.retriever.noun_gloss is None
    # "payroll" is not a corpus word: never mapped (keeps NO_EVIDENCE traps)
    assert bot.wordnet_noun.neighbours("payroll") == ()
    assert bot.grounder._term("payroll").kind == "unknown"


def test_bad_scope_rejected():
    import pytest

    with pytest.raises(ValueError):
        Copilot(config=CopilotConfig(use_wordnet_noun_sense=True, wordnet_scope="every"))


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


def test_lone_scope_maps_only_a_single_unknown_word():
    bot = Copilot(
        config=CopilotConfig(use_wordnet_noun_sense=True, wordnet_scope="lone", wordnet_max_path=1)
    )
    assert bot.retriever.noun_gloss is None
    one = {t.token: t for t in bot.grounder.terms("What is the upkeep window?")}
    assert one["upkeep"].kind == "wordnet_sense"
    assert "maintenance" in one["upkeep"].alts
    many = {t.token: t for t in bot.grounder.terms("What is the upkeep payroll connector?")}
    assert many["upkeep"].kind == "unknown"
    assert many["payroll"].kind == "unknown"
    # the suspend toggle is always released
    assert bot.wordnet_noun.suspend_unknown is False


def test_known_scope_never_maps_a_lone_unknown():
    bot = Copilot(config=CopilotConfig(use_wordnet_noun_sense=True, wordnet_max_path=1))
    one = {t.token: t for t in bot.grounder.terms("What is the upkeep window?")}
    assert one["upkeep"].kind == "unknown"
