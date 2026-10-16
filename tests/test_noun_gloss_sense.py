"""Ops noun gloss-sense: definitional bridges for lag/health, scan safety."""

from __future__ import annotations

from ops_copilot.config import CopilotConfig
from ops_copilot.noun_gloss_sense import (
    NounGlossSenseBackoff,
    build_sense_graph,
    load_ops_noun_senses,
    noun_bridges_from,
    sense_gloss_cosine,
)
from ops_copilot.pipeline import Copilot
from ops_copilot.synonym_split import load_split
from ops_copilot.text import fold_token
from ops_copilot.types import Decision


def test_ops_noun_seed_is_definitional_not_a_synonym_list() -> None:
    senses = load_ops_noun_senses()
    assert {s["word"] for s in senses} >= {"health", "status", "lag", "latency", "state"}
    for s in senses:
        assert s["pos"] == "noun"
        assert s.get("gloss")
        # Seed bridges via shared genus words; it must not list the hard pairs
        # as synonyms (that would be a hand-maintained synonym table).
        assert s.get("synonyms") in ([], None)


def test_sense_graph_bridges_lag_to_latency() -> None:
    graph = build_sense_graph()
    assert "lag" in graph and "latency" in graph
    hits = noun_bridges_from("lag")
    assert "latency" in hits
    assert hits["latency"].hops <= 2
    cos = sense_gloss_cosine("lag", "latency")
    assert cos is not None and cos >= 0.85


def test_sense_graph_bridges_health_to_status() -> None:
    hits = noun_bridges_from("health")
    assert "status" in hits
    assert hits["status"].hops <= 2
    cos = sense_gloss_cosine("health", "status")
    assert cos is not None and cos >= 0.85


def test_scan_image_cosine_below_noun_gate() -> None:
    # Verb-graph grounding rewrote scan->image and broke a clean no-evidence
    # trap; the noun gate's min_gloss_cosine must reject that pair.
    cos = sense_gloss_cosine("scan", "image")
    assert cos is None or cos < 0.85


def test_neighbours_return_latency_and_status_not_image() -> None:
    from ops_copilot.pipeline import Copilot as C

    corpus = frozenset(C().grounder.idf)
    gs = NounGlossSenseBackoff(corpus_words=corpus)
    lag = {n.word for n in gs.neighbours("lag")}
    health = {n.word for n in gs.neighbours("health")}
    scan = {n.word for n in gs.neighbours("scan")}
    assert "latency" in lag
    assert "status" in health or "state" in health
    assert "image" not in scan


def test_heldout_lag_and_health_answer_with_noun_gloss_sense() -> None:
    bot = Copilot(config=CopilotConfig(use_noun_gloss_sense=True))
    assert bot.ask("What is the current checkout p99 lag?").decision is Decision.ANSWER
    assert bot.ask("What is the health of the payments-api?").decision is Decision.ANSWER


def test_heldout_lag_and_health_refuse_when_noun_gloss_off() -> None:
    bot = Copilot(config=CopilotConfig(use_noun_gloss_sense=False))
    assert bot.ask("What is the current checkout p99 lag?").decision is not Decision.ANSWER
    assert bot.ask("What is the health of the payments-api?").decision is not Decision.ANSWER


def test_pci_dss_no_evidence_trap_stays_no_evidence() -> None:
    bot = Copilot(config=CopilotConfig(use_noun_gloss_sense=True))
    r = bot.ask("What is the PCI DSS scan cadence for the vault cluster?")
    assert r.decision is Decision.REFUSE_NO_EVIDENCE


def test_seed_and_graph_are_external_style_resources() -> None:
    """Held-out words may appear in the seed/extract; product maps stay clean."""
    held = {fold_token(w) for w in load_split()["heldout_words"]}
    seed_words = {s["word"] for s in load_ops_noun_senses()}
    assert "lag" in seed_words and fold_token("lag") in held
    assert "health" in seed_words and fold_token("health") in held
