"""Word-meaning check on passage-support rescues (opt-in) and the d5-38 fail-open it closes."""

from __future__ import annotations

from dataclasses import replace

from ops_copilot.config import CopilotConfig
from ops_copilot.pipeline import Copilot
from ops_copilot.word_vectors import NeighbourTable

TRAP = "What colour is the checkout_retry feature flag?"


def _grounder(table):
    bot = Copilot(config=CopilotConfig())
    g = bot.grounder
    g.passage_sense = table
    return g


def test_sense_ok_needs_the_credited_word_among_the_query_words_substitutes():
    table = NeighbourTable(meta={"floor": 0.5}, neighbours={
        "colour": (("flush", 0.61),), "postponement": (("delays", 0.7),)})
    g = _grounder(table)
    assert not g.passage_sense_ok("colour", "default")
    assert g.passage_sense_ok("postponement", "delay")  # plural-folded match
    assert not g.passage_sense_ok("vitals", "status")  # no stored row fails closed


def test_no_table_means_no_check():
    assert _grounder(None).passage_sense_ok("colour", "default")


def test_config_default_is_off():
    assert CopilotConfig().passage_support_sense_check is False
    assert Copilot(config=CopilotConfig()).grounder.passage_sense is None


def test_the_check_closes_the_colour_default_rescue_end_to_end():
    on = Copilot(config=replace(CopilotConfig(), passage_support_sense_check=True))
    res = on.ask(TRAP)
    assert res.decision.value == "REFUSE_UNGROUNDED"
    assert on.ask("What is the current checkout p99 latency?").decision.value == "ANSWER"

