"""IBM Model 1 trainer, out-of-sample ranking eval and the committed table."""

from __future__ import annotations

import gzip
import json

import numpy as np
import pytest

from ops_copilot.corpus import Corpus
from ops_copilot.qa_translation import (
    DEFAULT_TABLE,
    AnswerSupportModel,
    build_table,
    clean_markdown,
    corpus_hash,
    is_test,
    is_valid,
    lift_scores,
    load_table,
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


def test_build_table_is_corpus_bound_and_sorted_by_lift():
    m = train_model1(_toy_pairs(), iterations=3, min_q_df=1, min_a_df=1)
    t = build_table(m, ["latency is high", "disk space"], {"source": "toy"})
    assert set(t["table"]) <= {"latency", "high", "disk", "space"}
    for rows in t["table"].values():
        lifts = [r[1] for r in rows]
        assert lifts == sorted(lifts, reverse=True)


# --- the committed table -----------------------------------------------------------


@pytest.fixture(scope="module")
def table() -> dict:
    return load_table()


def test_committed_table_matches_the_default_corpus(table):
    texts = [f"{c.title} {c.text}" for c in Corpus().chunks]
    assert table["meta"]["corpus_hash"] == corpus_hash(texts), (
        "corpus changed: rerun scripts/build_qa_translation.py"
    )


def test_committed_table_meta_records_source_licence_and_split(table):
    meta = table["meta"]
    assert all(lic.startswith("CC BY-SA") for lic in meta["licenses"])
    assert meta["n_test_pairs"] > 1000 and meta["n_train_pairs"] > 10 * meta["n_test_pairs"] * 0.8
    assert len(meta["raw_sha256"]) == 64
    assert meta["em_iterations"] in (1, 2, 3, 5, 8)
    assert set(meta["sites"]) == {
        "serverfault", "superuser", "unix", "askubuntu", "dba", "security", "devops", "networkengineering"
    }


def test_committed_table_is_byte_stable(table):
    raw = gzip.decompress(DEFAULT_TABLE.read_bytes())
    assert raw == json.dumps(table, sort_keys=True, separators=(",", ":")).encode()


def test_answer_support_model_excludes_self_and_respects_threshold():
    texts = [f"{c.title} {c.text}" for c in Corpus().chunks]
    m = AnswerSupportModel(texts, min_score=float("-inf"))
    q, cands = next((q, c) for q, c in sorted(m._inv.items()) if len(c) >= 2)
    best_word = max(cands, key=lambda w: (cands[w], [-ord(ch) for ch in w]))
    got = m.best(q, list(cands))
    assert got is not None and got.evidence_word != q and got.score == max(
        s for w, s in cands.items() if w != q
    )
    strict = AnswerSupportModel(texts, min_score=got.score + 1e-6)
    assert strict.supports(q, [got.evidence_word]) is None
    assert best_word in cands


def test_corpus_change_without_rebuild_is_detected():
    with pytest.raises(ValueError, match="rerun scripts/build_qa_translation.py"):
        AnswerSupportModel(["a completely different corpus about gardening"])
