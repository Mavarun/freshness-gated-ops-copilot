from types import SimpleNamespace

import pytest

from ops_copilot.pipeline import Copilot
from ops_copilot.rewrite_suggest import (
    SuggestConfig,
    candidate_words,
    query_neighbours,
    suggest_rewrites,
    swap_word,
)
from ops_copilot.types import Decision


@pytest.fixture(scope="module")
def bot():
    return Copilot()


def test_swap_word_folds_plurals_and_keeps_case():
    assert swap_word("Who owns the Replicas?", "replica", "pods") == "Who owns the pods?"
    assert swap_word("What is the lag now?", "lag", "") == "What is the now?"
    assert swap_word("What is the lag now?", "missing", "x") is None


def test_query_neighbours_uses_content_tokens_only():
    nb = query_neighbours("What is the left error allowance for checkout?", "allowance", 2)
    assert nb == {"left", "error", "checkout"}


def test_only_ungrounded_refusals_get_suggestions(bot):
    ok = bot.ask("What is the current checkout p99 latency?")
    assert ok.decision == Decision.ANSWER
    assert suggest_rewrites(ok, bot) == []


def test_every_suggestion_is_verified_answer(bot):
    r = bot.ask("What is the left error allowance for checkout?")
    assert r.decision == Decision.REFUSE_UNGROUNDED
    rws = suggest_rewrites(r, bot, SuggestConfig(rank="context"))
    assert rws, "expected at least one verified rewrite"
    for rw in rws:
        assert Copilot().ask(rw.query).decision == Decision.ANSWER
        assert rw.cited_ids


def test_context_rank_prefers_word_next_to_the_query_neighbours(bot):
    r = bot.ask("What is the left error allowance for checkout?")
    rws = suggest_rewrites(r, bot, SuggestConfig(rank="context"))
    assert rws[0].swaps == (("allowance", "budget"),)


def test_candidates_never_repeat_query_words_or_identifiers(bot):
    r = bot.ask("What is the present checkout p99 lag?")
    for rank in ("idf", "first"):
        words = candidate_words(r, bot, SuggestConfig(rank=rank))
        assert words
        assert not {"checkout", "present", "lag", "p99"} & set(words)
        assert all(w.isalpha() for w in words)


def test_unknown_rank_raises(bot):
    r = bot.ask("What is the present checkout p99 lag?")
    with pytest.raises(ValueError):
        candidate_words(r, bot, SuggestConfig(rank="nope"))


def test_drop_option_is_off_by_default(bot):
    r = bot.ask("What is the present checkout p99 lag?")
    assert all(rep for rw in suggest_rewrites(r, bot) for _, rep in rw.swaps)


def test_no_missing_terms_means_no_suggestions(bot):
    fake = SimpleNamespace(
        decision=Decision.REFUSE_UNGROUNDED, explanation={"missing_terms": []}, query="q", retrieved=[]
    )
    assert suggest_rewrites(fake, bot) == []


def test_min_context_filters_candidates_without_shared_neighbours(bot):
    from ops_copilot.rewrite_suggest import context_scores, ranked_for_term

    r = bot.ask("What is the left error allowance for checkout?")
    cfg = SuggestConfig(rank="context", min_context=1)
    kept = ranked_for_term(r, bot, "allowance", cfg)
    assert kept and kept[0] == "budget"
    scores = context_scores(r, "allowance", kept, cfg)
    assert all(scores[w] >= 1 for w in kept)
    assert len(kept) <= len(ranked_for_term(r, bot, "allowance", SuggestConfig(rank="context")))
