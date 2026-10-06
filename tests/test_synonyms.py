"""Corpus-side synonym/lemma map: anchored, separate from the eval's map, measured.

Since the held-out split the map holds dev words only; queries that used to
pass through held-out words (health ~ status, bounce/reboot ~ restart) are now
asserted to *refuse*, never to answer or propose a write.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from ops_copilot import Copilot, CopilotConfig
from ops_copilot.synonyms import (
    OPS_EQUIVALENTS,
    equivalents,
    fold_phrases,
    hyphen_variants,
    restart_verbs,
)
from ops_copilot.text import content_tokens
from ops_copilot.types import Decision

SRC = Path(__file__).resolve().parents[1] / "src" / "ops_copilot"
PRODUCT_MODULES = (
    "text.py",
    "lexicon.py",
    "synonyms.py",
    "grounding.py",
    "retrieve.py",
    "write_actions.py",
    "pii_redact.py",
    "pipeline.py",
    "policy.py",
    "semantic.py",
    "word_vectors.py",
    "config.py",
)


def test_groups_are_disjoint_and_anchored_in_the_corpus(copilot: Copilot) -> None:
    seen: set[str] = set()
    vocab = copilot.grounder.idf
    for group in OPS_EQUIVALENTS:
        assert not seen & set(group)
        seen |= set(group)
        anchor = group[0]
        # restart is a write verb the gate keys on, not a corpus term
        assert anchor == "restart" or anchor in vocab, anchor


def test_product_code_never_imports_the_eval_perturbation_map() -> None:
    banned = {"ops_copilot.perturb", "ops_copilot.synonym_split"}
    for name in PRODUCT_MODULES:
        tree = ast.parse((SRC / name).read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                assert node.module not in banned, name
            if isinstance(node, ast.Import):
                assert all(a.name not in banned for a in node.names), name


def test_equivalents_and_variants() -> None:
    assert "replicas" in equivalents("pods")
    assert "replicas" in equivalents("instances")
    assert "pods" not in equivalents("pods")
    assert equivalents("p99") == frozenset()
    assert equivalents("lag") == frozenset()  # deliberately excluded (consumer lag)
    assert "key" not in equivalents("secret")  # 'key' is overloaded
    assert equivalents("health") == frozenset()  # held out
    assert hyphen_variants("on-call") == frozenset({"oncall"})
    assert hyphen_variants("inc-4821") == frozenset()
    # no phrase folding left: "response time" holds held-out words
    assert fold_phrases("what is the checkout response time") == "what is the checkout response time"
    assert restart_verbs() == ("restart",)


def test_synonym_supports_grounding_but_unknown_word_does_not(copilot: Copilot) -> None:
    g = copilot.grounder
    ev = "Redis checkout-pool utilization is 98 percent of maxclients."
    assert g.keys_supported("What is the Redis checkout-pool usage?", ev)
    assert not g.keys_supported("What is the Redis checkout-pool wellness?", ev)
    term = {t.token: t for t in g.terms("How many checkout-api instances are running?")}
    assert term["instances"].kind == "synonym"
    assert "replicas" in term["instances"].alts


@pytest.mark.parametrize(
    ("query", "expected"),
    [
        ("What is the Redis checkout-pool usage?", Decision.ANSWER),
        ("How many checkout-api instances are running?", Decision.ANSWER),
        ("What is the auth secret TTL?", Decision.REFUSE_STALE),
        ("What is the incident bot slack bot secret?", Decision.REFUSE_PII),
    ],
)
def test_synonym_queries_reach_the_right_gate(copilot: Copilot, query: str, expected: Decision) -> None:
    assert copilot.ask(query).decision is expected


@pytest.mark.parametrize(
    "query",
    [
        "What is the health of the payments-api?",
        "Please bounce the checkout-api app now",
        "Can you reboot payments-worker?",
    ],
)
def test_heldout_synonyms_refuse_instead_of_guessing(copilot: Copilot, query: str) -> None:
    result = copilot.ask(query)
    assert result.decision not in {Decision.ANSWER, Decision.PROPOSE_WRITE}
    assert result.proposed_write is None


def test_synonym_map_off_is_the_ablation() -> None:
    bot = Copilot(config=CopilotConfig(use_synonyms=False))
    assert bot.ask("What is the Redis checkout-pool usage?").decision is Decision.REFUSE_UNGROUNDED
    assert bot.ask("How many checkout-api instances are running?").decision is not Decision.ANSWER


def test_synonyms_do_not_open_ungrounded_traps(copilot: Copilot) -> None:
    # 'playbook' ~ 'runbook' and 'rollback' ~ 'revert' are in the map; the
    # unknown content ('chargeback') and missing procedure still refuse.
    assert copilot.ask("What is the chargeback runbook for INC-4821?").decision in {
        Decision.REFUSE_UNGROUNDED,
        Decision.REFUSE_NO_EVIDENCE,
    }
    assert copilot.ask(
        "What is the revert procedure for the checkout_retry feature toggle?"
    ).decision is Decision.REFUSE_UNGROUNDED


def test_query_tokens_keep_heldout_phrases_unfolded(copilot: Copilot) -> None:
    toks = copilot.grounder._query_tokens("What is the checkout p99 response time?")
    assert "response" in toks and "time" in toks and "responsetime" not in toks
    assert "response" in content_tokens("What is the checkout p99 response time?")
