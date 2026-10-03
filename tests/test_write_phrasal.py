"""Phrasal-verb parser, cache-tool verbs and trailing conditionals."""

from __future__ import annotations

import pytest

from ops_copilot.ops_cli_verbs import CLI_VERB_INDEX, cli_words
from ops_copilot.synonym_split import load_split
from ops_copilot.text import fold_token
from ops_copilot.write_intent import AMBIGUOUS, PROPOSE, classify_write_intent
from ops_copilot.write_ontology import WriteActionType, lexicon_words
from ops_copilot.write_phrasal import PARTICLES, TOGGLE_PARTICLES, match_frame
from ops_copilot.write_targets import default_registry


def _held() -> set[str]:
    return {fold_token(w) for w in load_split()["heldout_words"]}


def test_resources_overlap_with_heldout_words_is_pinned() -> None:
    held = _held()
    # Closed-class particle list (Quirk et al. 1985): only "down" is held out.
    assert {fold_token(p) for p in PARTICLES} & held == {"down"}
    # Cache-tool command verbs: flush / purge are held out, ban / invalidate not.
    assert {fold_token(w) for w in cli_words()} & held == {"flush", "purge"}
    # The lexicons themselves stay clean (no "set", "turn", "bounce", ...).
    assert {fold_token(w) for w in lexicon_words()} & held == set()
    assert "bounce" not in CLI_VERB_INDEX and "bounce" not in lexicon_words()


@pytest.mark.parametrize(
    "query, action, target, value_key, value",
    [
        ("Switch promo_attach off", "toggle_flag", "promo_attach", "state", "off"),
        ("Flip on checkout_retry", "toggle_flag", "checkout_retry", "state", "on"),
        ("Turn off promo_attach", "toggle_flag", "promo_attach", "state", "off"),
        ("Set maxmemory-policy to allkeys-lru", "patch_config", "maxmemory-policy", "value", "allkeys-lru"),
        ("Move handshake_budget_ms to 250", "patch_config", "handshake_budget_ms", "value", "250"),
        ("Scale payments-worker down to 2", "scale_service", "payments-worker", None, None),
        ("Scale checkout-api up to 12 replicas", "scale_service", "checkout-api", None, None),
        ("Scale payments-worker in to 4 pods", "scale_service", "payments-worker", None, None),
    ],
)
def test_phrasal_writes_are_proposed(query, action, target, value_key, value) -> None:
    it = classify_write_intent(query)
    assert it.status == PROPOSE, it.reason
    assert it.action.value == action and it.target.name == target
    if value_key:
        assert it.payload.get(value_key) == value


def test_frames_carry_frame_confidence_not_lexicon_confidence() -> None:
    it = classify_write_intent("Switch promo_attach off")
    assert it.verb_source == "particle" and it.confidence == pytest.approx(0.9)


@pytest.mark.parametrize(
    "query, source",
    [
        ("Flush the checkout-cache", "ops_cli"),
        ("Purge checkout-cache", "ops_cli"),
        ("Ban checkout-cache", "ops_cli"),
        ("Invalidate the checkout-cache", "lexicon"),  # already a PR #13 lexicon verb
    ],
)
def test_cache_tool_verbs_clear_a_cache(query, source) -> None:
    it = classify_write_intent(query)
    assert it.status == PROPOSE
    assert it.action is WriteActionType.CLEAR_CACHE and it.target.name == "checkout-cache"
    assert it.verb_source == source


def test_cache_tool_verb_without_a_cache_object_is_not_proposed() -> None:
    assert classify_write_intent("Flush redis").status == AMBIGUOUS


def test_change_of_state_frame_only_vouches_for_settings() -> None:
    it = classify_write_intent("Set checkout-api to v2")
    assert it.status == AMBIGUOUS and it.reason_code == "kind_mismatch"


def test_bounce_stays_missed_but_never_proposed() -> None:
    it = classify_write_intent("Bounce checkout-api")
    assert it.status == AMBIGUOUS and it.reason_code == "unknown_verb"


@pytest.mark.parametrize(
    "query",
    [
        "Keep checkout_retry on",           # no-change verb
        "We flipped checkout_retry off last week",
        "Don't switch promo_attach off",
        "How do I scale payments-worker in?",
        "Should we switch promo_attach off?",
        "Log on to checkout-api and look at replicas",
    ],
)
def test_phrasal_lookalikes_are_not_writes(query) -> None:
    assert classify_write_intent(query).status != PROPOSE


@pytest.mark.parametrize(
    "query",
    [
        "Restart checkout-api if errors climb",
        "Switch promo_attach off if errors climb",
        "Restart checkout-api once the deploy lands",
        "Scale checkout-api up unless latency recovers",
    ],
)
def test_trailing_conditions_ask_instead_of_proposing(query) -> None:
    it = classify_write_intent(query)
    assert it.status == AMBIGUOUS and it.reason_code == "conditional"


def test_timing_phrases_are_not_conditions() -> None:
    assert classify_write_intent("Hey team, when you get a chance, scale up promo-service").status == PROPOSE
    assert classify_write_intent("Restart checkout-api before the freeze").status == PROPOSE


def test_knobs_turn_the_resources_off() -> None:
    assert classify_write_intent("Switch promo_attach off", phrasal=False).status != PROPOSE
    assert classify_write_intent("Ban checkout-cache", cli_verbs=False).status != PROPOSE


def test_toggle_particles_are_on_off() -> None:
    assert TOGGLE_PARTICLES == {"on", "off"}
    reg = default_registry()
    toks = "switch the promo_attach flag off".split()
    frame = match_frame(toks, 0, reg)
    assert frame is not None and frame.action is WriteActionType.TOGGLE_FLAG
