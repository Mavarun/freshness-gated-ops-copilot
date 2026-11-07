import dataclasses

from ops_copilot.config import CopilotConfig
from ops_copilot.pipeline import Copilot


def _bot(**kw):
    return Copilot(config=dataclasses.replace(CopilotConfig(), **kw))


def test_knob_is_off_by_default():
    assert CopilotConfig().passage_support_known_sense_check is False
    g = Copilot().grounder
    assert g.passage_sense is None and g.passage_sense_known_only is False


def test_known_random_word_rescue_is_closed():
    q = "What is the remaining error budget for max?"
    assert Copilot().ask(q).grounding.passage_rescued == ["max<-rate"]
    res = _bot(passage_support_known_sense_check=True).ask(q)
    assert res.decision.value == "REFUSE_UNGROUNDED"
    assert not res.grounding.passage_rescued


def test_unknown_word_rescue_is_untouched():
    # 'margin' is not a corpus word: known-only mode skips the check, the full check fails it
    q = "What is the remaining error margin for checkout?"
    assert _bot(passage_support_known_sense_check=True).ask(q).decision.value == "ANSWER"
    assert Copilot().ask(q).decision.value == "ANSWER"


def test_full_sense_check_wins_over_known_only():
    g = _bot(passage_support_known_sense_check=True, passage_support_sense_check=True).grounder
    assert g.passage_sense is not None and g.passage_sense_known_only is False
