"""IBM Model 1 trainer, lift scores and the out-of-sample ranking eval."""

from __future__ import annotations

import numpy as np

from ops_copilot.qa_translation import (
    clean_markdown,
    is_test,
    is_valid,
    lift_scores,
    pairs_from_page,
    query_log_likelihood,
    rank_eval,
    train_model1,
    words,
)


def _toy_pairs(n: int = 60) -> list[dict]:
    """Questions say 'lag' while their answers say 'latency' (plus shared noise)."""
    rng = np.random.default_rng(0)
    noise = ["server", "network", "config", "disk", "user", "file"]
    out = []
    for i in range(n):
        if i % 2 == 0:
            q, a = ["lag", "game"], ["latency", "ping", *rng.choice(noise, 2, replace=False)]
        else:
            q, a = ["disk", "full"], ["disk", "space", "delete", *rng.choice(noise, 2, replace=False)]
        out.append({"site": "toy", "qid": i, "aid": i, "q": q, "a": list(dict.fromkeys(a))})
    return out


def test_model1_learns_cross_word_translation():
    m = train_model1(_toy_pairs(), iterations=5, min_q_df=1, min_a_df=1)
    lift = lift_scores(m)
    qi = {w: i for i, w in enumerate(m.q_vocab)}
    ai = {w: i for i, w in enumerate(m.a_vocab)}

    def entry(q: str, a: str) -> float:
        k = np.where((m.qk == qi[q]) & (m.ak == ai[a]))[0]
        return float(lift[k[0]]) if len(k) else float("-inf")

    assert entry("lag", "latency") > 0.5
    assert entry("lag", "latency") > entry("lag", "disk")
    assert entry("full", "space") > entry("full", "latency")
    # EM never lowers the likelihood
    ll = [x["log_likelihood"] for x in m.log]
    assert all(b >= a - 1e-6 for a, b in zip(ll, ll[1:]))
    # T(.|a) is a distribution for every answer word
    sums = np.bincount(m.ak, weights=m.prob, minlength=len(m.a_vocab))
    assert np.allclose(sums[sums > 0], 1.0)


def test_model1_is_deterministic():
    a = train_model1(_toy_pairs(), iterations=3, min_q_df=1, min_a_df=1)
    b = train_model1(_toy_pairs(), iterations=3, min_q_df=1, min_a_df=1)
    assert np.array_equal(a.prob, b.prob)


def test_rank_eval_beats_chance_on_toy_data():
    pairs = _toy_pairs(80)
    train, test = pairs[:60], pairs[60:]
    m = train_model1(train, iterations=3, min_q_df=1, min_a_df=1)
    r = rank_eval(m, test, train, n_candidates=5, max_queries=20)
    assert r["translation"]["mrr"] > 1 / 5
    assert query_log_likelihood(m, ["lag"], ["latency"]) > query_log_likelihood(m, ["lag"], ["delete"])


def test_clean_markdown_drops_code_links_and_html():
    body = "Use `kubectl rollout`.\n\n    sudo rm -rf /\n\n```\ncode here\n```\nSee [the docs](http://x.y) <b>now</b> https://z.example"
    text = clean_markdown(body)
    for gone in ("kubectl", "sudo", "code here", "http", "<b>"):
        assert gone not in text
    assert "the docs" in text and "now" in text


def test_words_are_plain_folded_and_identifier_free():
    assert words("Kafka consumers lag on payments-worker p99 2410ms") == ["kafka", "consumer", "lag"]


def test_pairs_from_page_orders_accepted_first_and_skips_unvoted():
    page = {
        "items": [
            {
                "question_id": 7,
                "title": "Why is my latency so high?",
                "answers": [
                    {"answer_id": 1, "score": 9, "is_accepted": False, "body_markdown": "network congestion"},
                    {"answer_id": 2, "score": 2, "is_accepted": True, "body_markdown": "check the dns resolver"},
                    {"answer_id": 3, "score": 0, "is_accepted": False, "body_markdown": "reboot"},
                ],
            }
        ]
    }
    pairs = pairs_from_page("serverfault", page)
    assert [p["aid"] for p in pairs] == [2, 1]
    assert pairs[0]["q"] == ["latency", "high"]


def test_split_is_deterministic_disjoint_and_about_ten_percent():
    ids = range(20000)
    test = [i for i in ids if is_test("serverfault", i)]
    valid = [i for i in ids if is_valid("serverfault", i)]
    assert 0.08 < len(test) / 20000 < 0.12
    assert not set(test) & set(valid)
    assert test == [i for i in ids if is_test("serverfault", i)]
