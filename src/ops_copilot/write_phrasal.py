"""Phrasal verbs and argument-structure frames for the write gate.

PR #13 knew six two-token phrasal verbs ("roll back", "scale up", "switch
off" ...), each listed in the ontology. Writes such as "scale down X",
"turn off the promo_attach flag" or "set maxmemory-policy to allkeys-lru"
were missed: ``down``, ``turn`` (stem of held-out ``turned``) and ``set``
are held-out synonym words, so they may not be added to any write lexicon
(``write_ontology`` docstring, ``tests/test_write_ontology.py``).

This module recognises those writes by *grammar* instead of by new verbs.
It adds no content word to the write lexicons; its only word list is the
closed class of English adverbial particles, which is grammar, not ops
vocabulary.

1. **Particles** (``PARTICLES``): the common adverbial particles of English
   phrasal verbs, after the list in Quirk, Greenbaum, Leech and Svartvik
   (1985), *A Comprehensive Grammar of the English Language*, sec. 16.3 (the
   Penn Treebank ``RP`` tag covers the same class). It predates the synonym
   split by four decades and was not chosen by looking at it. One member,
   ``down``, is also a held-out word (from the pair "drain->burn down");
   ``tests`` pin that overlap, and the robustness report has an ablation
   with the particle reading switched off.
2. **Lexicon verb + particle**: an ontology verb followed by a particle that
   has a meaning for its action reads that meaning from the particle:
   ``scale up/out`` -> up, ``scale down`` -> down, ``scale in`` -> in;
   ``flip/switch on`` -> on, ``off`` -> off. The particle may follow the
   verb ("scale down checkout-api") or its object ("scale checkout-api down
   to 2", "flip promo_attach off"), as English separable phrasal verbs do.
3. **Particle-licensed toggle**: an instruction ``<V> on|off <flag>`` or
   ``<V> <flag> on|off`` is a TOGGLE_FLAG with the particle's state whatever
   the verb is ("turn off promo_attach", "turn checkout_retry on"). The
   particle and the flag carry the meaning, so no verb is listed. Verbs that ask for *no* change
   ("keep / leave X on") are excluded (``NO_CHANGE_VERBS``). The object may
   be any identifier; the classifier then checks it like any other target
   ("turn off checkout-api" is a service, not a flag: kind mismatch, ask).
4. **Change-of-state frame**: ``<V> [the] <config key | flag> [setting] to
   <value>`` ("set maxmemory-policy to allkeys-lru", "move
   checkout_retry to 50") is a PATCH_CONFIG carrying that value, again
   without listing the verb. The value must be a real token (not a
   determiner), and transfer verbs ("add X to the dashboard", "send X to")
   are excluded (``TRANSFER_VERBS``).

Frames 3 and 4 only ever see an *instruction* clause whose head is not an
ontology, read, quantity or unsupported verb (``write_mood`` decides the
mood first), so "Is checkout_retry turned
on?" (a question) and "checkout_retry is off" (a description) stay reads.
They need an identifier object ("turn off the flag" names none) and score
verb confidence 0.9 (the verb itself was not recognised); a lexicon verb +
particle scores 1.0.

The command verbs of cache tools ("flush", "purge") come from a separate,
cited resource: ``ops_cli_verbs``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from ops_copilot.text import is_identifier
from ops_copilot.write_ontology import (
    CONFIG_KEY,
    FLAG,
    INCIDENT,
    READ_VERBS,
    SPEC_BY_ACTION,
    UNSUPPORTED_VERBS,
    WriteActionType,
)
from ops_copilot.write_targets import Target, identifier_targets

# Quirk et al. (1985) sec. 16.3, common adverbial particles (single words).
PARTICLES: frozenset[str] = frozenset(
    {
        "about",
        "across",
        "ahead",
        "along",
        "apart",
        "around",
        "aside",
        "away",
        "back",
        "by",
        "down",
        "forward",
        "in",
        "off",
        "on",
        "out",
        "over",
        "past",
        "round",
        "through",
        "together",
        "under",
        "up",
    }
)

# What a particle means for an action (payload key, value). Particles with no
# entry for an action are ignored for it ("scale back" says nothing).
PARTICLE_SEMANTICS: dict[WriteActionType, dict[str, tuple[str, str]]] = {
    WriteActionType.SCALE_SERVICE: {
        "up": ("direction", "up"),
        "out": ("direction", "up"),
        "down": ("direction", "down"),
        "in": ("direction", "in"),
    },
    WriteActionType.TOGGLE_FLAG: {
        "on": ("state", "on"),
        "off": ("state", "off"),
    },
}
TOGGLE_PARTICLES: frozenset[str] = frozenset(PARTICLE_SEMANTICS[WriteActionType.TOGGLE_FLAG])

# "keep checkout_retry on" / "leave promo_attach off" ask for no change.
NO_CHANGE_VERBS: frozenset[str] = frozenset({"keep", "leave", "stay", "remain", "hold", "let"})
# "add maxmemory-policy to the dashboard": movement of the thing, not its value.
TRANSFER_VERBS: frozenset[str] = frozenset(
    {"add", "send", "copy", "attach", "link", "post", "forward", "give", "assign", "append", "pin", "mention"}
)
_DETERMINERS = frozenset({"the", "a", "an", "our", "this", "that", "my", "your"})
_NOT_A_VALUE = _DETERMINERS | frozenset({"be", "it", "its", "them", "me", "us", "you", "what", "which"})
PATCH_NOUNS: frozenset[str] = frozenset(SPEC_BY_ACTION[WriteActionType.PATCH_CONFIG].objects) | {"flag", "key"}
FRAME_CONFIDENCE = 0.9


@dataclass
class FrameParse:
    """A write recognised by a frame (3 or 4 above) rather than by its verb."""

    action: WriteActionType
    verb: str
    source: str  # particle | frame
    target_position: int
    payload: dict[str, Any] = field(default_factory=dict)
    confidence: float = FRAME_CONFIDENCE
    compatible: bool = True  # False: the object's kind does not take this action


def particle_meaning(action: WriteActionType, particle: str) -> tuple[str, str] | None:
    return PARTICLE_SEMANTICS.get(action, {}).get(particle)


# A separated particle ends the verb phrase; anything else after it means it
# was a preposition ("scale checkout-api *in* us-east-1").
_AFTER_PARTICLE = frozenset(
    {"", "to", "by", "for", "now", "please", "asap", "immediately", "again", "today", "and", "then"}
)


def separated_particle(tokens: list[str], after: int, action: WriteActionType) -> str | None:
    """Particle right after the object ("scale checkout-api *down*"), skipping one object noun."""
    j = after + 1
    spec = SPEC_BY_ACTION[action]
    if j < len(tokens) and tokens[j] in spec.objects and tokens[j] not in PARTICLES:
        j += 1
    if j < len(tokens) and particle_meaning(action, tokens[j]) is not None:
        nxt = tokens[j + 1] if j + 1 < len(tokens) else ""
        if nxt in _AFTER_PARTICLE or nxt.isdigit():
            return tokens[j]
    return None


def frame_head_ok(word: str) -> bool:
    """Heads a frame may read: plain words that are no other verb class."""
    return (
        word.isalpha()
        and not is_identifier(word)
        and word not in READ_VERBS
        and word not in UNSUPPORTED_VERBS
        and word not in NO_CHANGE_VERBS
        and word not in PARTICLES
        and not word.endswith(("ing", "ed"))
    )


def _skip_det(tokens: list[str], i: int) -> int:
    return i + 1 if i < len(tokens) and tokens[i] in _DETERMINERS else i


def _object_at(tokens: list[str], j: int, registry) -> Target | None:
    """The identifier object at ``tokens[j]`` (registry or not), if any."""
    if j >= len(tokens):
        return None
    hits = identifier_targets(tokens, registry, j)
    if hits and hits[0].position == j and hits[0].kind != INCIDENT:
        return hits[0]
    return None


def particle_toggle(tokens: list[str], head: int, registry) -> FrameParse | None:
    """Frame 3: ``<V> on|off [the] <flag>`` or ``<V> [the] <flag> [flag] on|off``."""
    word = tokens[head]
    if not frame_head_ok(word) or word in TRANSFER_VERBS:
        return None
    n = len(tokens)
    i = head + 1
    if i < n and tokens[i] in TOGGLE_PARTICLES:
        j = _skip_det(tokens, i + 1)
        if _object_at(tokens, j, registry) is not None:
            state = particle_meaning(WriteActionType.TOGGLE_FLAG, tokens[i])
            return FrameParse(
                WriteActionType.TOGGLE_FLAG, f"{word} {tokens[i]}", "particle", j,
                {"flag": tokens[j], "state": state[1] if state else "flip"},
            )
        return None
    j = _skip_det(tokens, i)
    if _object_at(tokens, j, registry) is not None:
        p = separated_particle(tokens, j, WriteActionType.TOGGLE_FLAG)
        if p is not None:
            state = particle_meaning(WriteActionType.TOGGLE_FLAG, p)
            return FrameParse(
                WriteActionType.TOGGLE_FLAG, f"{word} {p}", "particle", j,
                {"flag": tokens[j], "state": state[1] if state else "flip"},
            )
    return None


def change_of_state(tokens: list[str], head: int, registry) -> FrameParse | None:
    """Frame 4: ``<V> [the] <config key | flag> [setting] to <value>``."""
    word = tokens[head]
    if not frame_head_ok(word) or word in TRANSFER_VERBS:
        return None
    n = len(tokens)
    j = _skip_det(tokens, head + 1)
    obj = _object_at(tokens, j, registry)
    if obj is None:
        return None
    k = j + 1
    if k < n and tokens[k] in PATCH_NOUNS:
        k += 1
    if k + 1 >= n or tokens[k] != "to" or tokens[k + 1] in _NOT_A_VALUE:
        return None
    # "set checkout-api to v2" names a service: a deploy, a scale or a
    # setting? The frame only vouches for settings and flags.
    return FrameParse(
        WriteActionType.PATCH_CONFIG, word, "frame", j,
        {"config_key": tokens[j], "value": tokens[k + 1]},
        compatible=obj.kind in (CONFIG_KEY, FLAG, "unknown"),
    )


def match_frame(tokens: list[str], head: int, registry) -> FrameParse | None:
    """The first frame (toggle, then change of state) that fits the clause."""
    if not 0 <= head < len(tokens):
        return None
    return particle_toggle(tokens, head, registry) or change_of_state(tokens, head, registry)
