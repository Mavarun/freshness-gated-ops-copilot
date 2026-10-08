"""Stack Exchange Q&A pair extraction, cleaning and the train / test split."""

from __future__ import annotations

import pytest  # noqa: F401

from ops_copilot.qa_translation import (
    clean_markdown,
    is_test,
    is_valid,
    pairs_from_page,
    words,
)


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
