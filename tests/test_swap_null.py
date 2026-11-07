from ops_copilot.pipeline import Copilot
from ops_copilot.swap_null import (
    MECHANISMS,
    Row,
    build_swaps,
    corpus_words,
    golden_rows,
    mechanism,
    score,
)


def test_golden_rows_load_with_ids():
    rows = golden_rows()
    assert rows[0].id == "golden-00" and len(rows) == 51
    assert sum(r.expect == "ANSWER" for r in rows) == 14


def test_swaps_are_seeded_and_only_on_answered_rows():
    bot = Copilot()
    rows = [Row("a", "What is the current checkout p99 latency?", "ANSWER"),
            Row("b", "What colour is the checkout flag?", "REFUSE_UNGROUNDED")]
    s1 = build_swaps(rows, bot, draws=2, seed=7)
    s2 = build_swaps(rows, Copilot(), draws=2, seed=7)
    assert s1 == s2 and s1
    assert {s.row_id for s in s1} == {"a"}
    words = set(corpus_words(bot))
    assert all(s.word in words and s.word.lower() not in rows[0].query.lower().split() for s in s1)
    assert all(s.query != rows[0].query for s in s1)


def test_passage_rescue_of_a_random_word_is_attributed():
    bot = Copilot()
    res = bot.ask("What is the remaining error budget for max?")
    assert res.decision.value == "ANSWER"  # the leniency this module measures
    assert mechanism(res, "max") == "passage"
    assert mechanism(bot.ask("What is the current checkout p99 latency?"), "checkout") == "lexical"


def test_score_counts_rows_and_swaps():
    bot = Copilot()
    rows = [Row("a", "What is the remaining error budget for checkout?", "ANSWER"),
            Row("t", "What colour is the checkout_retry feature flag?", "REFUSE_UNGROUNDED")]
    swaps = build_swaps(rows, bot, draws=1, seed=3)
    sc = score(bot, rows, swaps)
    assert sc.n_answer_rows == 1 and sc.answered == 1
    assert sc.n_refuse_rows == 1 and sc.refuse_opened == 0
    assert sc.n_swaps == len(swaps) and sum(sc.by_mechanism.values()) == sc.passed
    assert set(sc.by_mechanism) == set(MECHANISMS)
    assert 0.0 <= sc.rates()["null_pass_rate"] <= 1.0
