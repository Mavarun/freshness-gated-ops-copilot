from __future__ import annotations

from collections import Counter

import pytest

from ops_copilot.eval import load_golden
from ops_copilot.perturb import (
    OPS_SYNONYMS,
    PERTURBATION_TYPES,
    perturb,
    perturb_all,
)

Q = "What is the current checkout p99 latency?"
IDENTIFIERS = ("checkout-api", "p99", "INC-4821", "CNRY-VAULT7F3A", "redis.maxmemory-policy")


@pytest.mark.parametrize("kind", PERTURBATION_TYPES)
def test_same_seed_same_output(kind: str) -> None:
    for case in load_golden():
        q = case["query"]
        assert perturb(q, kind, seed=7) == perturb(q, kind, seed=7)


def test_seed_changes_output_somewhere() -> None:
    queries = [c["query"] for c in load_golden()]
    a = [perturb_all(q, seed=1) for q in queries]
    b = [perturb_all(q, seed=2) for q in queries]
    assert a != b


@pytest.mark.parametrize("kind", PERTURBATION_TYPES)
def test_every_kind_changes_a_typical_query(kind: str) -> None:
    assert perturb(Q, kind) != Q


def test_unknown_kind_raises() -> None:
    with pytest.raises(ValueError):
        perturb(Q, "back_translate")


def test_synonym_swap_draws_from_map() -> None:
    out = perturb("Please restart the checkout-api service now", "synonym", seed=42)
    alts = set(OPS_SYNONYMS["restart"]) | set(OPS_SYNONYMS["service"])
    assert any(alt in out for alt in alts)
    assert "checkout-api" in out


def test_word_order_preserves_token_multiset_and_first_token() -> None:
    for case in load_golden():
        q = case["query"]
        out = perturb(q, "word_order")
        strip = lambda s: Counter(t.strip("?.!,") for t in s.split())  # noqa: E731
        assert strip(out) == strip(q)
        assert out.split()[0] == q.split()[0]


def test_typos_never_touch_identifiers() -> None:
    for case in load_golden():
        q = case["query"]
        out = perturb(q, "typo")
        for ident in IDENTIFIERS:
            if ident in q:
                assert ident in out
        assert len(out.split()) == len(q.split())


def test_polite_prefix_keeps_original_body() -> None:
    out = perturb(Q, "polite")
    assert out.endswith("what is the current checkout p99 latency?")
    imp = perturb("Please restart the checkout-api service now", "polite")
    assert imp.endswith("restart the checkout-api service now")
    assert "Please" not in imp
