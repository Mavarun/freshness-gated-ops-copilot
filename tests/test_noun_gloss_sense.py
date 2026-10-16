"""Ops noun gloss-sense: clean (non-held-out) seed, no-leak guards, scan safety."""

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
from ops_copilot.noun_gloss_sense import DATA_DIR, DEFAULT_OPS_NOUN_SEED, gloss_tokens
from ops_copilot.text import fold_token
from ops_copilot.types import Decision


def _held() -> set[str]:
    return {fold_token(w) for w in load_split()["heldout_words"]}


def test_ops_noun_seed_is_definitional_not_a_synonym_list() -> None:
    senses = load_ops_noun_senses()
    assert {s["word"] for s in senses} >= {"status", "latency"}
    for s in senses:
        assert s["pos"] == "noun"
        assert s.get("gloss")
        assert s.get("synonyms") in ([], None)


def test_seed_never_authors_or_mentions_a_heldout_word() -> None:
    """The first version of this seed wrote glosses for lag / health / state
    (all held-out) and fixed those rows: contamination. The product seed must
    contain no held-out headword and no held-out word inside any gloss."""
    held = _held()
    for s in load_ops_noun_senses():
        assert fold_token(s["word"]) not in held, s["word"]
        leaked = {fold_token(t) for t in gloss_tokens(s["gloss"])} & held
        assert not leaked, (s["word"], leaked)


def test_leaky_reference_seed_is_kept_only_as_labelled_reference() -> None:
    ref = DATA_DIR / "ops_noun_senses_leaky_reference.json"
    assert ref != DEFAULT_OPS_NOUN_SEED
    words = {s["word"] for s in load_ops_noun_senses(ref)}
    assert {"lag", "health"} <= words and words & _held()
    assert not (words & {s["word"] for s in load_ops_noun_senses()} & _held())


def test_clean_seed_does_not_bridge_lag_or_health() -> None:
    """Null result, recorded on purpose: with no hand-written gloss for the
    held-out words, the Wiktionary extract alone does not link them."""
    gate = CopilotConfig().noun_gloss_sense_min_gloss_cosine
    for a, b in (("lag", "latency"), ("health", "status")):
        cos = sense_gloss_cosine(a, b)
        assert cos is None or cos < gate, (a, b, cos)


def test_scan_image_cosine_below_noun_gate() -> None:
    cos = sense_gloss_cosine("scan", "image")
    assert cos is None or cos < 0.85


def test_neighbours_never_return_image_for_scan() -> None:
    corpus = frozenset(Copilot().grounder.idf)
    gs = NounGlossSenseBackoff(corpus_words=corpus)
    assert "image" not in {n.word for n in gs.neighbours("scan")}


def test_heldout_lag_and_health_not_answered_by_clean_noun_sense() -> None:
    for flag in (False, True):
        bot = Copilot(config=CopilotConfig(use_noun_gloss_sense=flag))
        assert bot.ask("What is the current checkout p99 lag?").decision is not Decision.ANSWER
        assert bot.ask("What is the health of the payments-api?").decision is not Decision.ANSWER


def test_pci_dss_no_evidence_trap_stays_no_evidence() -> None:
    bot = Copilot(config=CopilotConfig(use_noun_gloss_sense=True))
    r = bot.ask("What is the PCI DSS scan cadence for the vault cluster?")
    assert r.decision is Decision.REFUSE_NO_EVIDENCE


def test_noun_sense_is_off_by_default() -> None:
    assert CopilotConfig().use_noun_gloss_sense is False
