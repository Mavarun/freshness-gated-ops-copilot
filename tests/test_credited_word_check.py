"""Credited-word check: a generic passage word may not vouch for a missing query word."""

from dataclasses import replace

import pytest

from ops_copilot.config import CopilotConfig
from ops_copilot.domain_vectors import default_vectors
from ops_copilot.passage_support import credited_word_problems, neighbour_rank
from ops_copilot.pipeline import Copilot

AT2_01 = "What taste is the LaunchDarkly checkout_retry flag?"


@pytest.fixture(scope="module")
def dv():
    return default_vectors()


def test_stop_word_check_ships_on_and_the_other_two_stay_off():
    # on since its one-shot confirm (artifacts/credit_check_confirm.json)
    cfg = CopilotConfig()
    assert cfg.passage_support_credit_stop is True
    assert cfg.passage_support_credit_top_freq == 0
    assert cfg.passage_support_credit_max_rank == 0
    assert Copilot(config=cfg).grounder.credit_check_on
    off = replace(cfg, passage_support_credit_stop=False)
    assert not Copilot(config=off).grounder.credit_check_on


def test_off_returns_no_problem(dv):
    assert credited_word_problems(dv, "taste", "one") == ()


def test_stop_word_list_is_the_outside_one(dv):
    assert credited_word_problems(dv, "taste", "one", stop=True) == ("stop_word",)
    assert credited_word_problems(dv, "flavour", "other", stop=True) == ("stop_word",)
    assert credited_word_problems(dv, "plan", "schedule", stop=True) == ()


def test_frequency_uses_the_vector_table_order(dv):
    # the table is stored most-frequent first: "one" is index 3, "schedule" far down
    assert dv.index["one"] == 3
    assert credited_word_problems(dv, "taste", "one", top_freq=4) == ("frequent",)
    assert credited_word_problems(dv, "taste", "one", top_freq=3) == ()
    assert credited_word_problems(dv, "plan", "schedule", top_freq=100) == ()


def test_neighbour_rank_is_one_based_and_excludes_the_centre(dv):
    best = dv.neighbours("schedule", 1)[0][0]
    assert neighbour_rank(dv, "schedule", best) == 1
    assert neighbour_rank(dv, "schedule", "schedule") is None
    assert neighbour_rank(dv, "schedule", "zzzz-not-a-word") is None


def test_mutual_rank_vetoes_far_credits_only(dv):
    r = neighbour_rank(dv, "rotation", "renewal")
    assert credited_word_problems(dv, "renewal", "rotation", max_rank=r) == ()
    assert credited_word_problems(dv, "renewal", "rotation", max_rank=r - 1) == ("not_mutual",)
    assert credited_word_problems(dv, "renewal", "zzzz-unknown", max_rank=10) == ("not_mutual",)


def test_negative_settings_rejected(dv):
    with pytest.raises(ValueError):
        credited_word_problems(dv, "a", "b", top_freq=-1)


@pytest.mark.parametrize("knob", [{"passage_support_credit_stop": True},
                                  {"passage_support_credit_top_freq": 100},
                                  {"passage_support_credit_max_rank": 500}])
def test_each_knob_vetoes_the_spent_trap_at2_01_and_logs_the_credit(knob):
    # at2-01 is spent (traps v2 confirm, 2026-10-27); this pins the mechanism only.
    bot = Copilot(config=replace(CopilotConfig(), **knob))
    assert bot.ask(AT2_01).decision.value == "REFUSE_UNGROUNDED"
    query, word, credited, probs = bot.grounder.credit_log[0]
    assert (query, word, credited) == (AT2_01, "taste", "one") and probs


def test_veto_is_sticky_so_no_later_evidence_part_rescues_the_word():
    bot = Copilot(config=replace(CopilotConfig(), passage_support_credit_stop=True))
    bot.ask(AT2_01)
    # the shipped default reaches the null test three times for at2-01 (two parts
    # credit "bot"); with the sticky credit veto none of those calls happen
    assert bot.grounder.null_log == []
    assert len(bot.grounder.credit_log) == 1


def test_shipped_default_unchanged_on_golden_answers():
    off = Copilot(config=replace(CopilotConfig(), passage_support_credit_stop=False))
    on = Copilot(config=CopilotConfig())
    for q in ("What is the current checkout p99 latency?", "Is the checkout_retry feature flag enabled?",
              "What is the remaining error budget for checkout?"):
        assert on.ask(q).decision == off.ask(q).decision
