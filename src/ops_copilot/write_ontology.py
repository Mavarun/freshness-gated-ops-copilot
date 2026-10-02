"""Action ontology and verb-cluster lexicons for the structured write-intent parser.

The PR #12 write gate was three regexes (restart / page oncall / patch config).
This module replaces their vocabulary with a small, explicit action ontology:
each action has a verb cluster (single-token verbs and a few phrasal verbs),
the object nouns that pin it down when the verb alone is ambiguous, and the
target kinds it can act on (``write_targets`` extracts those from the corpus
registry). ``write_mood`` decides whether a clause is an instruction at all,
and ``write_intent`` puts the three together.

Leakage rule (same as ``synonyms.py``): no word of the robustness eval's
held-out synonym vocabulary (``data/golden/synonym_split.json``) and no
regular inflection of one may appear in any lexicon below, even when it is
ordinary ops vocabulary. ``tests/test_write_ontology.py`` enforces it. The
words left out on purpose, with the action they would have served:

- restart: ``bounce``, ``reboot``, ``recycle``, ``reinitialize``, ``kick``
  (and ``cycle``, an inflection stem of held-out ``cycling``);
- page: ``ping``; recipient ``engineer`` (as in "on-duty engineer");
- patch: ``set``, ``modify``, ``config``, ``configuration`` (and
  ``configure``, which shares the stem);
- deploy: ``rollout``;
- rotate: ``rollover``, ``cycle``, ``credential``, ``passphrase``;
- scale: ``down`` (so "scale down" parses as a scale with no direction),
  ``capacity``, ``count``;
- toggle: ``turn`` (inflection stem of held-out ``turned``);
- clear cache: ``flush``, ``purge``;
- generic: ``create``, ``list`` (also kept out of the read-verb list).

Dev words of the split (``update``, ``revert``, ``undo``, ``toggle``,
``switch``, ``alert``, ``on-duty``, ``pager``, ``lead``, ``clear``,
``release``, ``secret``, ``parameter``, ``value``) may stay: dev rows are
what they are measured on.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class WriteActionType(str, Enum):
    """Every mutating action the copilot may *propose* (never execute)."""

    RESTART_SERVICE = "restart_service"
    SCALE_SERVICE = "scale_service"
    ROLLBACK_DEPLOY = "rollback_deploy"
    DEPLOY_RELEASE = "deploy_release"
    PAGE_ONCALL = "page_oncall"
    TOGGLE_FLAG = "toggle_flag"
    ROTATE_SECRET = "rotate_secret"
    PATCH_CONFIG = "patch_config"
    CLEAR_CACHE = "clear_cache"


# Target kinds produced by ``write_targets.EntityRegistry``.
SERVICE = "service"
FLAG = "flag"
SECRET = "secret"
CONFIG_KEY = "config_key"
CACHE = "cache"
RECIPIENT = "recipient"
INCIDENT = "incident"
TARGET_KINDS: tuple[str, ...] = (SERVICE, FLAG, SECRET, CONFIG_KEY, CACHE, RECIPIENT, INCIDENT)


@dataclass(frozen=True)
class ActionSpec:
    """One ontology entry.

    ``verbs`` are base-form, single-token verbs; ``phrasal`` are two-token
    verbs ("roll back", "switch on"). ``objects`` are nouns that confirm the
    action when they follow the verb ("rotate the *token*"); ``needs_object``
    means the verb alone is too vague and one of them must be present.
    ``target_kinds`` are the registry kinds the action may act on, in
    preference order. ``anchor`` is the verb the corpus / golden set uses.
    """

    action: WriteActionType
    anchor: str
    verbs: tuple[str, ...]
    phrasal: tuple[str, ...] = ()
    objects: tuple[str, ...] = ()
    needs_object: bool = False
    target_kinds: tuple[str, ...] = ()
    description: str = ""
    payload_hint: dict = field(default_factory=dict)


ONTOLOGY: tuple[ActionSpec, ...] = (
    ActionSpec(
        WriteActionType.RESTART_SERVICE,
        anchor="restart",
        verbs=("restart", "relaunch", "respawn"),
        target_kinds=(SERVICE, CACHE),
        description="graceful restart of a workload",
        payload_hint={"graceful": True},
    ),
    ActionSpec(
        WriteActionType.SCALE_SERVICE,
        anchor="scale",
        verbs=("scale", "autoscale"),
        phrasal=("scale up", "scale out", "scale in"),
        objects=("replicas", "replica", "pods", "pod", "instances", "instance"),
        target_kinds=(SERVICE,),
        description="change the replica count of a workload",
    ),
    ActionSpec(
        WriteActionType.ROLLBACK_DEPLOY,
        anchor="rollback",
        verbs=("rollback", "revert", "undo"),
        phrasal=("roll back",),
        objects=("deploy", "deployment", "release", "change"),
        target_kinds=(SERVICE, FLAG, CONFIG_KEY),
        description="roll a workload back to its previous release",
    ),
    ActionSpec(
        WriteActionType.DEPLOY_RELEASE,
        anchor="deploy",
        verbs=("deploy", "redeploy", "release", "ship", "promote"),
        objects=("build", "version", "release", "canary"),
        target_kinds=(SERVICE,),
        description="deploy or promote a release",
    ),
    ActionSpec(
        WriteActionType.PAGE_ONCALL,
        anchor="page",
        verbs=("page", "escalate", "alert", "notify"),
        objects=(
            "oncall",
            "on-call",
            "on-duty",
            "pager",
            "primary",
            "secondary",
            "lead",
            "sre",
            "commander",
            "duty-manager",
        ),
        target_kinds=(RECIPIENT, INCIDENT),
        description="page / escalate to a human responder",
        payload_hint={"severity": "critical"},
    ),
    ActionSpec(
        WriteActionType.TOGGLE_FLAG,
        anchor="toggle",
        verbs=("enable", "disable", "toggle", "flip"),
        phrasal=("switch on", "switch off"),
        objects=("flag", "feature", "toggle", "switch"),
        target_kinds=(FLAG,),
        description="flip a feature flag",
    ),
    ActionSpec(
        WriteActionType.ROTATE_SECRET,
        anchor="rotate",
        verbs=("rotate", "regenerate", "renew", "reissue"),
        objects=("secret", "secrets", "token", "key", "password", "cert", "certificate", "approle"),
        target_kinds=(SECRET,),
        description="rotate a secret / token / certificate",
    ),
    ActionSpec(
        WriteActionType.PATCH_CONFIG,
        anchor="patch",
        verbs=("patch", "update", "change", "edit", "tune", "adjust"),
        objects=("setting", "parameter", "value", "policy", "limit", "timeout", "ttl"),
        target_kinds=(CONFIG_KEY, FLAG, SERVICE),
        description="change a setting / parameter value",
    ),
    ActionSpec(
        WriteActionType.CLEAR_CACHE,
        anchor="clear",
        verbs=("clear", "invalidate"),
        objects=("cache",),
        needs_object=True,
        target_kinds=(CACHE, SERVICE),
        description="clear / invalidate a cache",
    ),
)

SPEC_BY_ACTION: dict[WriteActionType, ActionSpec] = {s.action: s for s in ONTOLOGY}

# Verbs that change the replica count when their object is a replica noun
# ("increase checkout-api replicas to 20"); with any other object they are
# value changes and resolve to PATCH_CONFIG.
QUANTITY_VERBS: tuple[str, ...] = ("increase", "decrease", "raise", "lower", "reduce", "bump")
SCALE_OBJECTS = frozenset(SPEC_BY_ACTION[WriteActionType.SCALE_SERVICE].objects)

# Toggle direction from the verb ("enable" -> on). "switch on/off" carry it in
# the particle.
TOGGLE_STATE: dict[str, str] = {
    "enable": "on",
    "disable": "off",
    "switch on": "on",
    "switch off": "off",
}
SCALE_DIRECTION: dict[str, str] = {"scale up": "up", "scale out": "up", "scale in": "in"}

# Imperative verbs that ask for information, not a mutation. A clause headed
# by one of these is a read even without a question word ("show me the
# checkout-api replicas"). ("list" is held-out and therefore absent.)
READ_VERBS: frozenset[str] = frozenset(
    {
        "show",
        "display",
        "check",
        "describe",
        "explain",
        "inspect",
        "find",
        "summarize",
        "summarise",
        "look",
        "tell",
        "give",
        "fetch",
        "print",
        "review",
        "compare",
        "monitor",
        "watch",
        "investigate",
        "verify",
        "confirm",
        "read",
        "search",
        "lookup",
        "remind",
        "clarify",
        "document",
        "outline",
        "walk",
    }
)

# Mutations this copilot has no action for. Never proposed (and never routed
# to a nearby action by the prototype backoff); an instruction headed by one
# gets the ambiguous-write refusal instead.
UNSUPPORTED_VERBS: frozenset[str] = frozenset(
    {
        "delete",
        "remove",
        "destroy",
        "kill",
        "terminate",
        "stop",
        "drop",
        "wipe",
        "erase",
        "truncate",
        "uninstall",
        "shutdown",
        "rename",
        "migrate",
        "drain",
        "pause",
        "suspend",
        "resume",
        "cordon",
        "evict",
        "revoke",
        "grant",
        "approve",
        "merge",
        "execute",
    }
)

# A verb immediately followed by one of these nouns is used nominally
# ("restart policy for checkout-api", "release notes", "page rotation"), so
# it is not an instruction.
NOMINAL_FOLLOWERS: frozenset[str] = frozenset(
    {
        "policy",
        "procedure",
        "process",
        "runbook",
        "playbook",
        "notes",
        "note",
        "history",
        "log",
        "logs",
        "window",
        "schedule",
        "calendar",
        "cadence",
        "status",
        "plan",
        "checklist",
        "docs",
        "documentation",
        "rotation",
        "date",
        "reason",
        "budget",
        "train",
    }
)


def verb_index() -> dict[str, list[WriteActionType]]:
    """Single-token verb -> candidate actions (ontology order)."""
    out: dict[str, list[WriteActionType]] = {}
    for spec in ONTOLOGY:
        for v in spec.verbs:
            out.setdefault(v, []).append(spec.action)
    return out


def phrasal_index() -> dict[tuple[str, str], WriteActionType]:
    """Two-token phrasal verb -> action."""
    out: dict[tuple[str, str], WriteActionType] = {}
    for spec in ONTOLOGY:
        for p in spec.phrasal:
            a, b = p.split()
            out[(a, b)] = spec.action
    return out


def action_verbs() -> frozenset[str]:
    """Every single token a write lexicon keys on (verbs, particles, quantity verbs)."""
    words: set[str] = set(QUANTITY_VERBS)
    for spec in ONTOLOGY:
        words.update(spec.verbs)
        for p in spec.phrasal:
            words.update(p.split())
    return frozenset(words)


def lexicon_words() -> frozenset[str]:
    """Every token in every write lexicon (for the leakage test)."""
    words: set[str] = set(action_verbs())
    for spec in ONTOLOGY:
        words.add(spec.anchor)
        words.update(spec.objects)
    words |= READ_VERBS | UNSUPPORTED_VERBS | NOMINAL_FOLLOWERS
    return frozenset(words)
