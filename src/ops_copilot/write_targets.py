"""Target-entity extraction for proposed writes (service / flag / secret / key / pager).

``EntityRegistry`` is built from the corpus, not hand-listed: every
identifier-like token of the ops corpus (``checkout-api``, ``checkout_retry``,
``vault-transit``, ``cache-oncall``) is assigned a kind by its shape and its
immediate corpus context:

- ``recipient``: the token follows ``page`` / ``pager`` in the corpus, or ends
  in ``-oncall`` / ``-manager`` / ``-secrets`` (team mailboxes such as
  ``platform-secrets`` are escalation targets in this corpus, not secrets);
- ``flag``: an ``a_b`` token that sits next to the word ``flag``;
- ``secret``: ``-transit`` / ``-key`` / ``-token`` / ``-secret`` endings;
- ``cache``: ``-cache`` endings;
- ``config_key``: ``-policy`` / ``-budget`` / ``-cadence`` / ``-salt`` /
  ``-size`` / ``-ttl`` / ``-timeout`` / ``-limit`` endings, other ``a_b``
  tokens, and dotted keys (``redis.maxmemory-policy``);
- ``service``: ``-api`` / ``-worker`` / ``-service`` / ``-pool`` / ``-store``
  / ``-gate`` / ``-gateway`` / ``-proxy`` / ``-sidecar`` endings, plus the
  bare system names the corpus uses as workloads (``redis``, ``kafka``).

Incident ids (``inc-4821``), dates, sizes, metrics (``p99``, ``5xx``),
canary tokens and planted secrets never become targets.

``extract_target`` then reads the query tokens after the action verb and
returns the best candidate for the action's preferred kinds, with a
confidence: registry hit 1.0, unseen identifier with a known shape 0.85,
unseen identifier of unknown shape 0.7, a ``<modifier> <object noun>`` phrase
("the auth token", "the checkout retry flag") 0.7. No candidate means no
target, and the classifier asks for one instead of guessing.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Iterable

from ops_copilot.text import NON_SALIENT, is_identifier, normalize_text, tokenize
from ops_copilot.write_ontology import (
    CACHE,
    CONFIG_KEY,
    FLAG,
    INCIDENT,
    RECIPIENT,
    SECRET,
    SERVICE,
    SPEC_BY_ACTION,
    WriteActionType,
    action_verbs,
)

CORPUS_DIR = Path(__file__).resolve().parents[2] / "data" / "corpus"
CORPUS_FILES = ("ops_docs.jsonl", "canary_docs.jsonl", "pii_docs.jsonl")

_SUFFIX_KINDS: tuple[tuple[str, str], ...] = (
    ("-oncall", RECIPIENT),
    ("-on-call", RECIPIENT),
    ("-manager", RECIPIENT),
    ("-secrets", RECIPIENT),
    ("-transit", SECRET),
    ("-key", SECRET),
    ("-token", SECRET),
    ("-secret", SECRET),
    ("-cache", CACHE),
    ("-policy", CONFIG_KEY),
    ("-budget", CONFIG_KEY),
    ("-cadence", CONFIG_KEY),
    ("-salt", CONFIG_KEY),
    ("-size", CONFIG_KEY),
    ("-ttl", CONFIG_KEY),
    ("-timeout", CONFIG_KEY),
    ("-limit", CONFIG_KEY),
    ("-api", SERVICE),
    ("-worker", SERVICE),
    ("-service", SERVICE),
    ("-svc", SERVICE),
    ("-pool", SERVICE),
    ("-store", SERVICE),
    ("-gate", SERVICE),
    ("-gateway", SERVICE),
    ("-proxy", SERVICE),
    ("-sidecar", SERVICE),
)
# Bare system names the corpus treats as workloads.
SYSTEM_NAMES: dict[str, str] = {"redis": SERVICE, "kafka": SERVICE}

_NOT_A_TARGET = re.compile(
    r"^(?:inc|ops|sev|cnry|about|q\d|p\d+|akia|xoxb)[-\d]|"  # ids, canaries, planted keys
    r"^[\d][\d\-:./]*[a-z]{0,3}$|"  # dates, times, sizes (400ms, 2gb, 5xx)
    r"^p\d+$|^v\d+$|^k8s$|"
    r"^[a-z]{2}-[a-z]+-\d+$"  # cloud regions (us-east-1) scope a write, they are not its target
)
_INCIDENT = re.compile(r"^inc-\d+$")
_PAGE_WORDS = frozenset({"page", "pager", "paging", "paged"})

# Generic head nouns: "restart the payments *service*" names the workload by
# the modifier in front of them.
GENERIC_SERVICE_NOUNS = frozenset(
    {"service", "services", "app", "application", "workload", "deployment", "worker", "api", "cluster"}
)


def shape_kind(token: str) -> str | None:
    """Kind implied by an identifier's shape alone (None = unknown shape)."""
    if _NOT_A_TARGET.search(token):
        return None
    for suffix, kind in _SUFFIX_KINDS:
        if token.endswith(suffix) and len(token) > len(suffix):
            return kind
    if "." in token and re.search(r"[a-z]\.[a-z]", token):
        return CONFIG_KEY
    if "_" in token:
        return CONFIG_KEY
    return None


def _candidate_token(token: str) -> bool:
    return is_identifier(token) and any(ch.isalpha() for ch in token) and not _NOT_A_TARGET.search(token)


@dataclass
class EntityRegistry:
    """name -> kind for every workload / flag / secret / key / pager in the corpus."""

    kinds: dict[str, str] = field(default_factory=dict)

    @classmethod
    def from_texts(cls, texts: Iterable[str]) -> "EntityRegistry":
        kinds: dict[str, str] = {}
        for text in texts:
            toks = tokenize(text)
            for i, tok in enumerate(toks):
                prev = toks[i - 1] if i else ""
                nxt = toks[i + 1] if i + 1 < len(toks) else ""
                if tok in SYSTEM_NAMES:
                    kinds.setdefault(tok, SYSTEM_NAMES[tok])
                    continue
                if not _candidate_token(tok):
                    continue
                if prev in _PAGE_WORDS:
                    kinds[tok] = RECIPIENT  # context beats shape
                    continue
                kind = shape_kind(tok)
                if kind == CONFIG_KEY and "_" in tok and "flag" in (prev, nxt):
                    kind = FLAG
                if kind is not None:
                    kinds.setdefault(tok, kind)
        return cls(kinds)

    @classmethod
    def from_corpus_files(cls, corpus_dir: Path = CORPUS_DIR) -> "EntityRegistry":
        texts: list[str] = []
        for name in CORPUS_FILES:
            path = corpus_dir / name
            if not path.is_file():
                continue
            for line in path.read_text(encoding="utf-8").splitlines():
                if line.strip():
                    row = json.loads(line)
                    texts.append(f"{row.get('title', '')}. {row.get('body', '')}")
        return cls.from_texts(texts)

    def kind(self, token: str) -> str | None:
        return self.kinds.get(token)

    def names(self, kind: str | None = None) -> list[str]:
        return sorted(n for n, k in self.kinds.items() if kind is None or k == kind)

    def as_dict(self) -> dict[str, list[str]]:
        out: dict[str, list[str]] = {}
        for name, kind in sorted(self.kinds.items()):
            out.setdefault(kind, []).append(name)
        return out


@lru_cache(maxsize=1)
def default_registry() -> EntityRegistry:
    """Registry of the committed corpus (cached per process)."""
    return EntityRegistry.from_corpus_files()


@dataclass(frozen=True)
class Target:
    name: str
    kind: str
    source: str  # registry | identifier | phrase | context | recipient
    confidence: float
    position: int = -1

    def as_dict(self) -> dict:
        return {
            "name": self.name,
            "kind": self.kind,
            "source": self.source,
            "confidence": round(self.confidence, 3),
        }


def identifier_targets(tokens: list[str], registry: EntityRegistry, start: int = 0) -> list[Target]:
    """Every identifier / system-name candidate at or after ``start``."""
    out: list[Target] = []
    for i in range(start, len(tokens)):
        tok = tokens[i]
        kind = registry.kind(tok)
        if kind is not None:
            out.append(Target(tok, kind, "registry", 1.0, i))
            continue
        tail = tok.rsplit(".", 1)[-1] if "." in tok else ""
        if tail and registry.kind(tail) is not None:
            # redis.maxmemory-policy: a dotted path ending in a registry key
            out.append(Target(tok, registry.kind(tail), "registry", 1.0, i))
            continue
        if _INCIDENT.match(tok):
            out.append(Target(tok, INCIDENT, "registry", 1.0, i))
            continue
        if not _candidate_token(tok):
            continue
        kind = shape_kind(tok)
        if kind is not None:
            out.append(Target(tok, kind, "identifier", 0.85, i))
        else:
            out.append(Target(tok, "unknown", "identifier", 0.7, i))
    return out


_PHRASE_STOP = action_verbs() | frozenset({"to", "for", "with", "on", "in", "at", "from", "and"})


def phrase_target(tokens: list[str], start: int, heads: Iterable[str], kind: str) -> Target | None:
    """``<modifier...> <head noun>`` after ``start`` ("the auth token" -> "auth")."""
    heads = frozenset(heads)
    for i in range(start, len(tokens)):
        if tokens[i] in heads:
            mods: list[str] = []
            j = i - 1
            while j >= start and tokens[j] not in NON_SALIENT and tokens[j] not in _PHRASE_STOP:
                mods.insert(0, tokens[j])
                j -= 1
            if mods:
                return Target(" ".join(mods), kind, "phrase", 0.7, j + 1)
            return None
        if tokens[i] in ("to", "for", "with"):
            break
    return None


_PAGE_CONTEXT = re.compile(r"\bfor\s+(?:the\s+)?(?P<ctx>[\w.-]+(?:\s+[\w.-]+)*?)(?:\s+now)?\s*$")


def page_target(normalized: str, tokens: list[str], start: int, registry: EntityRegistry) -> tuple[Target | None, str | None]:
    """(target, recipient) for a page: the ``for ...`` context, else the recipient.

    Matches the PR #12 contract: "page the oncall for the payments outage" ->
    target "payments outage"; with no ``for`` clause the target is the
    recipient ("primary" for the generic on-call words).
    """
    recips = SPEC_BY_ACTION[WriteActionType.PAGE_ONCALL].objects
    recipient: str | None = None
    for tok in tokens[start:]:
        if tok == "for":
            break
        if registry.kind(tok) == RECIPIENT:
            recipient = tok
            break
        if tok in recips or tok.replace("-", "") in {r.replace("-", "") for r in recips}:
            recipient = tok
            break
    # The for-clause is searched after the verb only.
    head = " ".join(tokens[:start])
    tail = normalized[len(head):] if normalized.startswith(head) else normalized
    m = _PAGE_CONTEXT.search(tail)
    if m:
        ctx = m.group("ctx").strip("-. ")
        if ctx:
            return Target(ctx, INCIDENT, "context", 0.9), recipient
    if recipient is not None:
        generic = recipient.replace("-", "") in {"oncall", "onduty", "pager", "primary"}
        name = "primary" if generic else recipient
        return Target(name, RECIPIENT, "recipient", 0.85), recipient
    return None, None


def normalized_tokens(text: str) -> list[str]:
    """Whitespace tokens of ``normalize_text`` (identifiers intact)."""
    return normalize_text(text).split()
