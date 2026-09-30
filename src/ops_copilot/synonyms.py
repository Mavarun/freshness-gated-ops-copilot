"""Corpus-side ops equivalence map used by grounding, retrieval, and the write gate.

This is *not* the robustness eval's perturbation map (``perturb.OPS_SYNONYMS``)
and must never import it. It is written from the corpus side: every group is
anchored on a term that appears in ``data/corpus`` (or on a write verb the gate
keys on) and lists spellings an on-call engineer would treat as the same
thing. Groups the eval's map uses but that are ambiguous in ops prose were left
out on purpose, e.g. ``lag`` (consumer lag is its own metric), ``owner`` ~
``contact`` (conflates the PII owner directory with the allowlisted contact),
``key`` ~ ``secret`` (``key`` is also a config key / Redis key), ``seed`` ~
``salt``, ``left`` ~ ``remaining``, ``live`` ~ ``production``. ``db`` ~
``database`` was tried and dropped: in this corpus ``db`` only occurs as a
doc-title prefix ("db cfg 31") and it lifted the database-password trap from
REFUSE_NO_EVIDENCE to REFUSE_UNGROUNDED on the clean golden set.

Leakage-free (heldout-synonyms slice): the eval's synonym vocabulary is split into dev
and held-out words (``synonym_split.py``, seed 42, 64 of 127 novel words held
out; ``data/golden/synonym_split.json``). Every held-out word was deleted from
the groups and phrases below, even standard ops vocabulary, and groups left
with a single member were dropped. ``restart`` keeps a one-member group only
because the write gate reads its verb list from here. Dev words may stay; they
are what the dev rows measure. ``tests/test_heldout_leakage.py`` asserts no
held-out word is in this map or in the semantic-backoff glossary, and
``robustness.leakage_report`` reports dev and held-out coverage separately
(held-out coverage must be 0).

Rules:

- groups are bidirectional; a query word matches evidence containing any word
  of its group (after the usual plural fold);
- multi-word phrases (``OPS_PHRASES``, currently none) are rewritten to a
  single group member before tokenizing;
- hyphen/space spelling variants (``oncall`` / ``on-call``, ``e-mail`` /
  ``email``) are equivalent without needing an entry (``hyphen_variants``);
- identifiers with digits (``p99``, ``inc-4821``) are never expanded.
"""

from __future__ import annotations

import re

# Each tuple is one equivalence group; the first member is the corpus anchor.
OPS_EQUIVALENTS: tuple[tuple[str, ...], ...] = (
    # write verbs (the restart gate keys on this group; synonyms held out)
    ("restart",),
    # workload / capacity
    ("replicas", "instances", "pods"),
    ("utilization", "usage"),
    ("qps", "rps", "throughput"),
    # state / incident vocabulary
    ("incident", "outage"),
    ("mitigation", "remediation"),
    ("runbook", "playbook"),
    ("procedure", "process"),
    ("rollback", "revert"),
    ("target", "goal"),
    # deploy
    ("deploy", "deployment", "release"),
    ("production", "prod"),
    ("flag", "toggle"),
    # networking
    ("endpoint", "url"),
    # credentials
    ("token", "secret"),
)

# Multi-word spellings folded to one token before tokenizing. Empty since the
# held-out split: "response time" and "requests per second" contain held-out
# words, and "request rate" -> qps shares the plural-folded form of the
# held-out word "requests", so it went too (strict reading of the rule).
OPS_PHRASES: tuple[tuple[str, str], ...] = ()

_GROUP_OF: dict[str, frozenset[str]] = {}
for _group in OPS_EQUIVALENTS:
    _members = frozenset(_group)
    for _word in _group:
        if _word in _GROUP_OF:
            raise ValueError(f"synonym {_word!r} is in two groups")
        _GROUP_OF[_word] = _members

_PHRASE_RES = tuple(
    (re.compile(rf"(?<![\w-]){re.escape(src)}(?![\w-])"), dst) for src, dst in OPS_PHRASES
)


def equivalents(token: str) -> frozenset[str]:
    """Group members for ``token`` (excluding itself); empty if none."""
    if any(ch.isdigit() for ch in token):
        return frozenset()
    group = _GROUP_OF.get(token)
    if group is None and len(token) > 4 and token.endswith("s"):
        group = _GROUP_OF.get(token[:-1])
    return (group or frozenset()) - {token}


def fold_phrases(normalized: str) -> str:
    """Rewrite known multi-word spellings in already-normalized text."""
    out = normalized
    for rx, dst in _PHRASE_RES:
        out = rx.sub(dst, out)
    return out


def hyphen_variants(token: str) -> frozenset[str]:
    """Spelling variants that differ only by a hyphen (oncall ~ on-call)."""
    if any(ch.isdigit() for ch in token):
        return frozenset()
    if "-" in token:
        return frozenset({token.replace("-", "")})
    return frozenset()


def restart_verbs() -> tuple[str, ...]:
    """Verbs the write gate treats as ``restart`` (anchor first)."""
    return OPS_EQUIVALENTS[0]
