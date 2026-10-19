"""WordNet morphy noun lemmatisation (synthetic table; no eval words)."""

from ops_copilot.config import CopilotConfig
from ops_copilot.pipeline import Copilot
from ops_copilot.wordnet_senses import NOUN_DETACHMENTS, WordNetNounSense, WordNetTable, noun_base_forms

TABLE = WordNetTable(
    meta={"corpus_words": ["gadget", "device"]},
    neighbours={
        "berry": (("gadget", "syn", 0, 0, 0),),
        "box": (("device", "syn", 0, 0, 0),),
        "church": (("gadget", "syn", 0, 0, 0),),
        "fireman": (("device", "hyper", 1, 0, 0),),
        "widget": (("gadget", "syn", 0, 0, 0),),
    },
)


def test_detachment_rules_follow_wordnet_order():
    assert NOUN_DETACHMENTS[0] == ("s", "") and NOUN_DETACHMENTS[-1] == ("ies", "y")
    assert noun_base_forms("berries", TABLE.neighbours) == ("berry",)
    assert noun_base_forms("boxes", TABLE.neighbours) == ("box",)
    assert noun_base_forms("churches", TABLE.neighbours) == ("church",)
    assert noun_base_forms("firemen", TABLE.neighbours) == ("fireman",)
    assert noun_base_forms("widgets", TABLE.neighbours) == ("widget",)


def test_only_known_bases_and_never_the_token_itself():
    assert noun_base_forms("widget", TABLE.neighbours) == ()
    assert noun_base_forms("zebras", TABLE.neighbours) == ()
    assert noun_base_forms("ss", {"": ()}) == ()


def test_morphy_off_keeps_the_old_lookup():
    off = WordNetNounSense(max_path=1, table=TABLE)
    on = WordNetNounSense(max_path=1, table=TABLE, morphy=True)
    assert off.neighbours("berries") == ()
    assert [n.word for n in on.neighbours("berries")] == ["gadget"]
    # fold_token already covered a plain -s plural before morphy.
    assert [n.word for n in off.neighbours("widgets")] == ["gadget"]


def test_morphy_respects_the_known_only_scope():
    b = WordNetNounSense(max_path=1, table=TABLE, morphy=True, known_only=True)
    assert b.neighbours("berries") == ()


def test_config_flag_reaches_the_backoff_and_is_off_by_default():
    assert CopilotConfig().wordnet_morphy is False
    bot = Copilot(config=CopilotConfig(use_wordnet_noun_sense=True, wordnet_morphy=True))
    assert bot.wordnet_noun.morphy is True
