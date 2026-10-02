"""Structured write-intent classifier: ontology + target + mood (+ optional prototypes).

``classify_write_intent`` returns one of three outcomes:

- ``propose``: an instruction clause whose head is an ontology verb, with a
  target of a compatible kind and a confidence of at least
  ``min_confidence``. The pipeline turns it into a PENDING ``ProposedWrite``
  (action, target, payload, confidence, parse trace); nothing executes
  without a human approve.
- ``ambiguous``: it looks like an instruction to mutate something but the
  parser cannot pin it down: no target, several targets or actions, a
  conditional ("if X, restart Y"), an unsupported mutation ("delete
  checkout-api"), an unrecognised verb aimed at a known entity ("please
  <verb> checkout-api"), or low confidence. The policy answers with
  ``REFUSE_AMBIGUOUS_WRITE`` and asks the user to restate.
- ``none``: not a write (questions, read verbs, descriptions, negations).

Confidence = verb x mood x target x kind-compatibility, each in (0, 1]:
lexicon / phrasal verb 1.0, keyboard-typo of a lexicon verb 0.9, a quantity
verb resolved by its object ("increase ... replicas") 0.9; bare or framed
instruction 1.0, inverted "can restart you X" 0.9; target confidences from
``write_targets``; a target kind the action does not take x0.6. The default
``min_confidence`` 0.65 means a registry target or a specific identifier is
needed for a typo'd verb, and an incompatible target ("rotate
checkout-api") is never proposed.

With ``mood_detection=False`` (the "lexicon parser only" ablation) the first
ontology verb anywhere in a clause is taken as the instruction, with no
informational exemption; it exists to measure what the mood detector buys.

The optional prototype backoff (``write_prototypes``) is consulted only for
an instruction clause shaped ``<unknown verb> [the] <entity>`` and can only
upgrade that clause from ``ambiguous`` to ``propose`` when the nearest
dev-built action prototype clears the calibrated similarity and margin.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol

from ops_copilot.lexicon import is_keyboard_typo
from ops_copilot.text import is_identifier
from ops_copilot.write_mood import INSTRUCTION_MOODS, Clause, Mood, analyze_mood
from ops_copilot.write_ontology import (
    INCIDENT,
    NOMINAL_FOLLOWERS,
    QUANTITY_VERBS,
    SCALE_DIRECTION,
    SCALE_OBJECTS,
    SPEC_BY_ACTION,
    TOGGLE_STATE,
    UNSUPPORTED_VERBS,
    WriteActionType,
    action_verbs,
    phrasal_index,
    verb_index,
)
from ops_copilot.write_targets import (
    GENERIC_SERVICE_NOUNS,
    EntityRegistry,
    Target,
    default_registry,
    identifier_targets,
    page_target,
    phrase_target,
)

PROPOSE = "propose"
AMBIGUOUS = "ambiguous"
NONE = "none"
DEFAULT_MIN_CONFIDENCE = 0.65
INCOMPATIBLE_KIND = 0.6
TYPO_VERB = 0.9
QUANTITY_VERB = 0.9

_VERBS = verb_index()
_PHRASAL = phrasal_index()
_WRITE_VERBS = action_verbs()
_SNAP_TARGETS = tuple(sorted(v for v in _VERBS if len(v) >= 5))
_DETERMINERS = frozenset({"the", "a", "an", "our", "this", "that", "my", "your"})
# Words that may trail "<verb> [the] <entity>" without changing its shape.
_TRAILERS = frozenset(
    {"now", "please", "asap", "immediately", "again", "today", "quickly", "for", "me", "us"}
) | GENERIC_SERVICE_NOUNS


class PrototypeMatcher(Protocol):
    def match(self, verb: str, target_kind: str) -> dict | None: ...


@dataclass
class ActionParse:
    action: WriteActionType | None
    verb: str
    verb_source: str  # lexicon | phrasal | typo | quantity | unsupported | unknown | nominal | prototype
    verb_confidence: float
    object_start: int
    target: Target | None = None
    extra_targets: list[Target] = field(default_factory=list)
    payload: dict[str, Any] = field(default_factory=dict)
    compatible: bool = True
    prototype: dict | None = None


@dataclass
class WriteIntent:
    status: str
    query: str
    reason: str
    mood: str = Mood.EMPTY.value
    action: WriteActionType | None = None
    verb: str = ""
    verb_source: str = ""
    target: Target | None = None
    payload: dict[str, Any] = field(default_factory=dict)
    confidence: float = 0.0
    clause: str = ""
    prototype: dict | None = None

    @property
    def is_write(self) -> bool:
        return self.status == PROPOSE

    def parse_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "reason": self.reason,
            "mood": self.mood,
            "action": self.action.value if self.action else None,
            "verb": self.verb,
            "verb_source": self.verb_source,
            "target": self.target.as_dict() if self.target else None,
            "confidence": round(self.confidence, 3),
            "clause": self.clause,
            "prototype": self.prototype,
        }


def _snap_verb(word: str) -> str | None:
    """Unique lexicon verb one keyboard slip from ``word`` (inflections excluded)."""
    if len(word) < 5 or not word.isalpha() or word in _VERBS:
        return None
    hits = []
    for verb in _SNAP_TARGETS:
        if word.startswith(verb) or verb.startswith(word):
            return None  # restarts / restarted are descriptions, not typos
        if is_keyboard_typo(word, verb):
            hits.append(verb)
    return hits[0] if len(hits) == 1 else None


def _next_after(tokens: list[str], idx: int, word: str) -> str | None:
    for j in range(idx, len(tokens) - 1):
        if tokens[j] == word:
            return tokens[j + 1]
    return None


def _number_after(tokens: list[str], start: int) -> int | None:
    for j in range(start, len(tokens)):
        if tokens[j].isdigit():
            return int(tokens[j])
    return None


def parse_action(tokens: list[str], head: int, registry: EntityRegistry, *, typo_tolerance: bool = True) -> ActionParse:
    """Action, verb and target for the instruction headed at ``tokens[head]``."""
    word = tokens[head]
    nxt = tokens[head + 1] if head + 1 < len(tokens) else ""
    verb_conf, source = 1.0, "lexicon"
    action: WriteActionType | None = None
    verb = word
    start = head + 1
    if word not in _VERBS and (word, nxt) not in _PHRASAL and word not in QUANTITY_VERBS and typo_tolerance:
        snapped = _snap_verb(word)
        if snapped is not None:
            word, verb, verb_conf, source = snapped, snapped, TYPO_VERB, "typo"
    if nxt in NOMINAL_FOLLOWERS and (word in _VERBS or word in UNSUPPORTED_VERBS):
        return ActionParse(None, verb, "nominal", 0.0, start)
    if (word, nxt) in _PHRASAL:
        action, verb, source, start = _PHRASAL[(word, nxt)], f"{word} {nxt}", "phrasal", head + 2
    elif word in _VERBS:
        action = _VERBS[word][0]
    elif word in QUANTITY_VERBS:
        rest = set(tokens[head + 1 :])
        action = (
            WriteActionType.SCALE_SERVICE if rest & SCALE_OBJECTS else WriteActionType.PATCH_CONFIG
        )
        source, verb_conf = "quantity", QUANTITY_VERB
    elif word in UNSUPPORTED_VERBS:
        parse = ActionParse(None, verb, "unsupported", 0.0, start)
        ids = identifier_targets(tokens, registry, start)
        parse.target = ids[0] if ids else None
        return parse
    else:
        parse = ActionParse(None, verb, "unknown", 0.0, start)
        ids = identifier_targets(tokens, registry, start)
        parse.target = ids[0] if ids else None
        return parse

    spec = SPEC_BY_ACTION[action]
    if spec.needs_object:
        has_obj = any(t in spec.objects for t in tokens[start:])
        ids = identifier_targets(tokens, registry, start)
        if not has_obj and not any(t.kind in spec.target_kinds[:1] for t in ids):
            return ActionParse(None, verb, "unknown", 0.0, start, target=ids[0] if ids else None)
    parse = ActionParse(action, verb, source, verb_conf, start)
    _attach_target(parse, tokens, registry)
    return parse


def _attach_target(parse: ActionParse, tokens: list[str], registry: EntityRegistry) -> None:
    action = parse.action
    assert action is not None
    spec = SPEC_BY_ACTION[action]
    start = parse.object_start
    if action is WriteActionType.PAGE_ONCALL:
        target, recipient = page_target(" ".join(tokens), tokens, start, registry)
        parse.target = target
        parse.payload = {
            "recipient": recipient or (target.name if target else None),
            "severity": "critical",
        }
        return
    ids = [t for t in identifier_targets(tokens, registry, start) if t.kind != INCIDENT]
    compatible = [t for t in ids if t.kind in spec.target_kinds]
    unknown = [t for t in ids if t.kind == "unknown"]
    chosen: Target | None = None
    if compatible:
        chosen = compatible[0]
    elif unknown:
        chosen = unknown[0]
    elif ids:
        chosen, parse.compatible = ids[0], False
    if chosen is None:
        heads = spec.objects or ()
        if spec.target_kinds and spec.target_kinds[0] == "service":
            heads = tuple(heads) + tuple(GENERIC_SERVICE_NOUNS)
        if heads:
            chosen = phrase_target(tokens, start, heads, spec.target_kinds[0])
    parse.target = chosen
    # Only further entities of the same kind compete with the chosen target
    # ("restart checkout-api and payments-api"); an unknown-shape identifier
    # next to a registry target is a qualifier, not a second write.
    others = [t for t in compatible if chosen is not None and t.name != chosen.name and t.kind == chosen.kind]
    parse.extra_targets = others
    name = chosen.name if chosen else None
    if action is WriteActionType.RESTART_SERVICE:
        parse.payload = {"service": name, "graceful": True}
    elif action is WriteActionType.SCALE_SERVICE:
        direction = SCALE_DIRECTION.get(parse.verb)
        if parse.verb in ("increase", "raise", "bump"):
            direction = "increase"
        elif parse.verb in ("decrease", "lower", "reduce"):
            direction = "decrease"
        parse.payload = {"service": name, "replicas": _number_after(tokens, start), "direction": direction}
    elif action is WriteActionType.ROLLBACK_DEPLOY:
        parse.payload = {"service": name, "to": "previous"}
    elif action is WriteActionType.DEPLOY_RELEASE:
        parse.payload = {"service": name, "version": _next_after(tokens, start, "to")}
    elif action is WriteActionType.TOGGLE_FLAG:
        parse.payload = {"flag": name, "state": TOGGLE_STATE.get(parse.verb, "flip")}
    elif action is WriteActionType.ROTATE_SECRET:
        parse.payload = {"secret": name}
    elif action is WriteActionType.CLEAR_CACHE:
        parse.payload = {"cache": name}
    elif action is WriteActionType.PATCH_CONFIG:
        value = None
        if chosen is not None and chosen.position >= 0:
            value = _next_after(tokens, chosen.position, "to")
            if value is None:
                later = [t for t in identifier_targets(tokens, registry, chosen.position + 1)]
                value = later[0].name if later else None
        parse.payload = {"config_key": name}
        if value:
            parse.payload["value"] = value
        # The value is not a second target.
        parse.extra_targets = [t for t in parse.extra_targets if t.name != value]


def _unknown_verb_shape(tokens: list[str], head: int, target: Target | None) -> bool:
    """``<verb> [det] <entity> [trailers]``: an instruction aimed at a known entity."""
    if target is None or target.position < 0:
        return False
    word = tokens[head]
    if not word.isalpha() or is_identifier(word) or word.endswith(("ing", "ed")):
        return False
    gap = tokens[head + 1 : target.position]
    if any(t not in _DETERMINERS for t in gap) or len(gap) > 1:
        return False
    return all(t in _TRAILERS for t in tokens[target.position + 1 :])


def _first_lexicon_verb(tokens: list[str], typo_tolerance: bool) -> int:
    for i, tok in enumerate(tokens):
        nxt = tokens[i + 1] if i + 1 < len(tokens) else ""
        if tok in _VERBS or (tok, nxt) in _PHRASAL or tok in QUANTITY_VERBS:
            return i
        if typo_tolerance and _snap_verb(tok):
            return i
    return -1


def classify_write_intent(
    query: str,
    *,
    registry: EntityRegistry | None = None,
    typo_tolerance: bool = True,
    mood_detection: bool = True,
    prototypes: PrototypeMatcher | None = None,
    min_confidence: float = DEFAULT_MIN_CONFIDENCE,
) -> WriteIntent:
    """Classify ``query`` as a write proposal, an ambiguous write, or not a write."""
    q = (query or "").strip()
    reg = registry if registry is not None else default_registry()
    mood = analyze_mood(q, typo_tolerance=typo_tolerance, write_verbs=_WRITE_VERBS)
    if not mood.clauses:
        return WriteIntent(NONE, q, "empty query", mood.mood.value)
    if mood_detection and mood.mood is Mood.INFORMATIONAL and mood.cue:
        return WriteIntent(NONE, q, f"informational cue {mood.cue!r}", mood.mood.value)

    parses: list[tuple[Clause, ActionParse]] = []
    for clause in mood.clauses:
        if mood_detection:
            if clause.mood not in INSTRUCTION_MOODS and clause.mood is not Mood.CONDITIONAL:
                continue
            head = clause.head
        else:
            head = _first_lexicon_verb(clause.tokens, typo_tolerance)
            clause = Clause(clause.tokens, head, Mood.IMPERATIVE, "lexicon_only", 1.0)
        if head < 0:
            continue
        parses.append((clause, parse_action(clause.tokens, head, reg, typo_tolerance=typo_tolerance)))

    actions = [(c, p) for c, p in parses if p.action is not None]
    if not actions:
        return _no_lexicon_action(q, mood.mood, parses, prototypes, mood_detection, min_confidence, reg)
    distinct = {(p.action, p.target.name if p.target else None) for _, p in actions}
    if len(distinct) > 1:
        return WriteIntent(
            AMBIGUOUS, q, "several write actions in one request; ask for one at a time",
            mood.mood.value, clause=" | ".join(" ".join(c.tokens) for c, _ in actions),
        )
    clause, parse = actions[0]
    second = _second_action_verb(clause, typo_tolerance)
    if second is not None:
        return WriteIntent(
            AMBIGUOUS, q, f"second write verb {second!r} in the same request; ask for one at a time",
            mood.mood.value, clause=" ".join(clause.tokens),
        )
    return _finish(q, clause, parse, min_confidence)


def _second_action_verb(clause: Clause, typo_tolerance: bool) -> str | None:
    """A coordinated second instruction verb (``... and restart it``) after the head."""
    toks = clause.tokens
    for i in range(max(clause.head, 0) + 1, len(toks) - 1):
        if toks[i] in {"and", "then", "also"}:
            nxt = toks[i + 1]
            if nxt in _WRITE_VERBS:
                return nxt
    return None


def _finish(q: str, clause: Clause, parse: ActionParse, min_confidence: float) -> WriteIntent:
    base = dict(
        query=q,
        mood=clause.mood.value,
        action=parse.action,
        verb=parse.verb,
        verb_source=parse.verb_source,
        target=parse.target,
        payload=dict(parse.payload),
        clause=" ".join(clause.tokens),
        prototype=parse.prototype,
    )
    if clause.mood is Mood.CONDITIONAL:
        return WriteIntent(AMBIGUOUS, reason="conditional instruction; restate it once the condition holds", **base)
    if parse.target is None:
        return WriteIntent(AMBIGUOUS, reason="write verb without a specific target", **base)
    if parse.extra_targets:
        names = [parse.target.name] + [t.name for t in parse.extra_targets]
        return WriteIntent(AMBIGUOUS, reason=f"several targets {names}; one write per request", **base)
    conf = (
        parse.verb_confidence
        * (clause.confidence or 1.0)
        * parse.target.confidence
        * (1.0 if parse.compatible else INCOMPATIBLE_KIND)
    )
    base["confidence"] = conf
    if conf < min_confidence:
        why = "target kind does not fit the action" if not parse.compatible else "low confidence"
        return WriteIntent(AMBIGUOUS, reason=f"{why} ({conf:.2f} < {min_confidence:.2f})", **base)
    return WriteIntent(PROPOSE, reason=f"{parse.verb_source} verb {parse.verb!r} -> {parse.action.value}", **base)


def _no_lexicon_action(
    q: str,
    overall: Mood,
    parses: list[tuple[Clause, ActionParse]],
    prototypes: PrototypeMatcher | None,
    mood_detection: bool,
    min_confidence: float,
    registry: EntityRegistry,
) -> WriteIntent:
    if not mood_detection:
        return WriteIntent(NONE, q, "no ontology verb", overall.value)
    for clause, parse in parses:
        if parse.verb_source == "unsupported" and parse.target is not None:
            return WriteIntent(
                AMBIGUOUS, q, f"unsupported mutation {parse.verb!r}; no action exists for it",
                clause.mood.value, verb=parse.verb, verb_source="unsupported", target=parse.target,
                clause=" ".join(clause.tokens),
            )
        if parse.verb_source != "unknown" or not _unknown_verb_shape(clause.tokens, clause.head, parse.target):
            continue
        target = parse.target
        assert target is not None
        match = prototypes.match(parse.verb, target.kind) if prototypes is not None else None
        common = dict(
            query=q, mood=clause.mood.value, verb=parse.verb, target=target,
            clause=" ".join(clause.tokens), prototype=match,
        )
        if match and match.get("accepted"):
            action = WriteActionType(match["action"])
            proto_parse = ActionParse(action, parse.verb, "prototype", float(match["confidence"]), parse.object_start)
            _attach_target(proto_parse, clause.tokens, _with_target(registry, target))
            proto_parse.prototype = match
            if proto_parse.target is None:
                proto_parse.target = target
            return _finish(q, clause, proto_parse, min_confidence)
        why = "unrecognised action verb {!r} aimed at {!r}".format(parse.verb, target.name)
        if match:
            why += f" (nearest prototype {match['action']} cos={match['cosine']:.2f} rejected: {match['why']})"
        return WriteIntent(AMBIGUOUS, reason=why, verb_source="unknown", **common)
    return WriteIntent(NONE, q, "no instruction with a write verb", overall.value)


def _with_target(registry: EntityRegistry, target: Target) -> EntityRegistry:
    if registry.kind(target.name) is None:
        return EntityRegistry({**registry.kinds, target.name: target.kind})
    return registry
