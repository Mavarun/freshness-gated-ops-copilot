"""Typo tolerance: keyboard-slip edits snap to unique corpus words; identifiers never."""

from __future__ import annotations

import random

import pytest

from ops_copilot import Copilot, CopilotConfig
from ops_copilot.eval import load_golden
from ops_copilot.lexicon import (
    QWERTY_NEIGHBOURS,
    CorpusVocabulary,
    damerau_levenshtein,
    is_keyboard_typo,
    within_one_edit,
)
from ops_copilot.text import normalize_text
from ops_copilot.types import Decision


def test_within_one_edit_matches_osa_distance() -> None:
    rng = random.Random(7)
    for _ in range(3000):
        a = "".join(rng.choice("abcd") for _ in range(rng.randint(0, 6)))
        b = "".join(rng.choice("abcd") for _ in range(rng.randint(0, 6)))
        assert within_one_edit(a, b) == (damerau_levenshtein(a, b) <= 1)


def test_qwerty_neighbours_are_symmetric_layout_neighbours() -> None:
    assert {"f", "h", "t", "y", "v", "b"} == set(QWERTY_NEIGHBOURS["g"])
    for key, near in QWERTY_NEIGHBOURS.items():
        for other in near:
            assert key in QWERTY_NEIGHBOURS[other]


@pytest.mark.parametrize(
    ("typo", "word", "ok"),
    [
        ("checkuot", "checkout", True),  # transposition
        ("rnning", "running", True),  # dropped letter
        ("eeror", "error", True),  # doubled / neighbour extra
        ("enabked", "enabled", True),  # neighbour key
        ("interval", "internal", False),  # v->n is not a neighbour key
        ("patch", "path", False),  # extra 'c' is not near t/h
        ("latency", "latency", False),  # identical is not a typo
    ],
)
def test_keyboard_typo_model(typo: str, word: str, ok: bool) -> None:
    assert is_keyboard_typo(typo, word) is ok


def test_vocabulary_correction_rules() -> None:
    vocab = CorpusVocabulary([["checkout", "replicas", "vault", "slack", "wait"]], extra_words={"what", "want"})
    assert vocab.correct("checkuot") == "checkout"
    assert vocab.correct("vualt") == "vault"
    assert vocab.correct("slak") == "slack"  # 4 chars: first/last kept
    assert vocab.correct("checkout-apl") is None  # identifier: exact only
    assert vocab.correct("p98") is None
    assert vocab.correct("xz") is None
    assert vocab.correct("waht") is None  # tie: what / want
    assert vocab.is_typo_of_any("waht", frozenset({"what", "want"}))
    assert vocab.correct("zzzzzz") is None


def test_clean_golden_queries_are_never_typo_rewritten(copilot: Copilot) -> None:
    for case in load_golden():
        q = case["query"]
        assert not [t for t in copilot.grounder.terms(q) if t.kind == "typo"], q
        rewritten = copilot.retriever.rewrite_query(q).split()
        assert set(rewritten) <= set(normalize_text(q).split()) | {
            w for t in copilot.grounder.terms(q) for w in t.alts
        }, q


@pytest.mark.parametrize(
    ("query", "expected"),
    [
        ("What is the crrent checkuot p99 latency?", Decision.ANSWER),
        ("Wht is the sttus of the payments-api?", Decision.ANSWER),
        ("What is the Rediis maxmemory-policy?", Decision.REFUSE_STALE),
        ("What is the pqger bridge webhook route?", Decision.REFUSE_CANARY),
        ("Can you rrstart payments-worker?", Decision.PROPOSE_WRITE),
        ("Please pathc the redis.maxmemory-policy connfig to allkeys-lru", Decision.PROPOSE_WRITE),
    ],
)
def test_typo_queries_reach_the_right_gate(copilot: Copilot, query: str, expected: Decision) -> None:
    assert copilot.ask(query).decision is expected


def test_typo_tolerance_can_be_switched_off() -> None:
    bot = Copilot(config=CopilotConfig(typo_tolerance=False))
    assert bot.ask("What is the crrent checkuot p99 latency?").decision is Decision.REFUSE_UNGROUNDED


def test_typo_in_unknown_trap_word_does_not_open_it(copilot: Copilot) -> None:
    # "millicroe" is one slip from "millicore", which is not in the corpus either.
    result = copilot.ask("What millicroe CPU request is configured on checkout-api?")
    assert result.decision is Decision.REFUSE_UNGROUNDED
