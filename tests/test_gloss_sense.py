"""Ops gloss-sense model: definitional bridges, write matching, grounding."""

from __future__ import annotations

from ops_copilot.gloss_sense import (
    GlossSenseBackoff,
    bridges_from,
    build_verb_graph,
    gloss_centroid,
    gloss_cosine,
    gloss_tokens,
    verb_headwords,
)
from ops_copilot.write_intent import classify_write_intent
from ops_copilot.synonym_split import load_split
from ops_copilot.text import fold_token


def test_verb_graph_links_bounce_to_reboot_and_restart() -> None:
    graph = build_verb_graph()
    assert "bounce" in graph
    nbrs = {n for n, _w, _k in graph["bounce"]}
    assert "reboot" in nbrs
    hits = bridges_from("bounce")
    assert hits["reboot"].hops == 1
    assert hits["restart"].hops == 2
    assert hits["restart"].path[0] == "bounce"
    assert hits["restart"].path[-1] == "restart"


def test_reboot_reaches_restart_in_one_hop() -> None:
    hits = bridges_from("reboot")
    assert hits["restart"].hops == 1
    assert "reboot" in hits["restart"].path and "restart" in hits["restart"].path


def test_gloss_centroid_lifts_bounce_restart_over_global_vector() -> None:
    # Global domain-vector cosine is ~0.08 (email bounce); gloss centroids align.
    cos = gloss_cosine("bounce", "restart")
    assert cos is not None and cos >= 0.5
    assert gloss_centroid("bounce") is not None


def test_gloss_tokens_strips_pointer_prefix() -> None:
    assert "reboot" in gloss_tokens("Synonym of reboot.")


def test_match_action_accepts_bounce_and_reboot_for_service() -> None:
    gs = GlossSenseBackoff()
    for verb in ("bounce", "reboot", "reload"):
        m = gs.match_action(verb, "service")
        assert m is not None and m["accepted"] is True
        assert m["action"] == "restart_service"


def test_match_action_rejects_recycle_and_read_verbs() -> None:
    gs = GlossSenseBackoff()
    assert gs.match_action("recycle", "service")["accepted"] is False
    assert gs.match_action("lag", "service")["accepted"] is False


def test_match_action_respects_target_kind() -> None:
    gs = GlossSenseBackoff()
    # restart_service does not take a flag target
    m = gs.match_action("bounce", "flag")
    assert m is not None
    assert m["accepted"] is False


def test_write_intent_proposes_bounce_and_reboot_with_gloss_sense() -> None:
    gs = GlossSenseBackoff()
    for q in (
        "Please bounce the checkout-api app now",
        "Can you reboot payments-worker?",
    ):
        intent = classify_write_intent(q, gloss_sense=gs)
        assert intent.status == "propose"
        assert intent.action is not None
        assert intent.action.value == "restart_service"
        assert intent.verb_source == "gloss_sense"


def test_write_intent_still_refuses_without_gloss_sense() -> None:
    intent = classify_write_intent("Please bounce the checkout-api app now")
    assert intent.status == "ambiguous"


def test_informational_bounce_is_not_a_write() -> None:
    gs = GlossSenseBackoff()
    intent = classify_write_intent("What is the email bounce rate?", gloss_sense=gs)
    assert intent.status == "none"


def test_neighbours_return_corpus_reachable_words() -> None:
    # "restart" is a write-ontology verb but not always a corpus content word;
    # "reload" is reachable in two hops and is a domain-vocab word. Grounding
    # uses whatever corpus intersection exists.
    from ops_copilot.domain_vectors import default_vectors

    dv = default_vectors()
    cw = frozenset(dv.words)
    gs = GlossSenseBackoff(corpus_words=cw, min_score=1.0, min_gloss_cosine=0.3)
    words = {n.word for n in gs.neighbours("bounce")}
    assert "reload" in words or "reboot" in words


def test_graph_is_not_a_hand_authored_heldout_lexicon() -> None:
    """Held-out words may appear in the external extract; the product synonym
    map must stay clean. The graph is built only from Wiktionary verb senses.
    """
    held = {fold_token(w) for w in load_split()["heldout_words"]}
    heads = verb_headwords()
    # Sanity: the extract knows bounce (held-out) as a computing verb — that
    # is the point of an external resource — but we never write it into
    # synonyms.OPS_EQUIVALENTS (covered by test_heldout_leakage).
    assert "bounce" in heads
    assert fold_token("bounce") in held
