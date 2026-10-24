"""Word-meaning check on passage-support rescues (opt-in) and the d5-38 fail-open it closes."""

from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

import pytest

from ops_copilot.config import CopilotConfig
from ops_copilot.pipeline import Copilot
from ops_copilot.word_vectors import NeighbourTable

ART = Path(__file__).resolve().parents[1] / "artifacts" / "passage_sense_probe.json"
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


@pytest.mark.xfail(strict=True, reason="shipped default answers d5-38 via passage rescue colour<-default "
                                        "(2026-10-24); the opt-in check closes it but loses 36 correct calibration rows")
def test_the_shipped_default_refuses_the_colour_trap():
    assert Copilot().ask(TRAP).decision.value == "REFUSE_UNGROUNDED"


def test_probe_artifact_closes_d5_38_but_fails_the_no_new_error_rule():
    rep = json.loads(ART.read_text())
    assert rep["post_hoc"] is True and rep["n_rows"] == 171
    assert rep["default"]["opened_must_refuse"] == ["d5-38"] and rep["sense_check"]["opened_must_refuse"] == []
    assert (rep["default"]["correct"], rep["sense_check"]["correct"]) == (92, 57)
    assert (rep["default"]["answer_correct"], rep["sense_check"]["answer_correct"]) == (26, 9)
    assert rep["fixed"] == ["d5-38"] and len(rep["new_errors"]) == 36
    assert rep["sense_check"]["clean"]["clean_accuracy"] == 1.0 and rep["sweep_labelled_trap_opened"] == []
