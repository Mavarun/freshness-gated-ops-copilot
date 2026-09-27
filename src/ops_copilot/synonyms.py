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

Overlap with the eval's map is unavoidable for standard ops vocabulary
(``reboot`` ~ ``restart``, ``pods`` ~ ``replicas``); ``robustness.leakage_report``
measures it and the README reports it next to an ablation with this map off.

Rules:

- groups are bidirectional; a query word matches evidence containing any word
  of its group (after the usual plural fold);
- multi-word phrases (``response time``) are rewritten to a single group
  member before tokenizing;
- hyphen/space spelling variants (``oncall`` / ``on-call``, ``e-mail`` /
  ``email``) are equivalent without needing an entry (``hyphen_variants``);
- identifiers with digits (``p99``, ``inc-4821``) are never expanded.
"""

from __future__ import annotations

import re

# Each tuple is one equivalence group; the first member is the corpus anchor.
OPS_EQUIVALENTS: tuple[tuple[str, ...], ...] = (
    # write verbs (the restart gate keys on this group)
    ("restart", "reboot", "bounce", "recycle"),
    # workload / capacity
    ("replicas", "instances", "pods"),
    ("utilization", "usage"),
    ("latency", "responsetime"),
    ("qps", "rps", "throughput"),
    # state / incident vocabulary
    ("status", "health"),
    ("incident", "outage", "downtime"),
    ("mitigation", "remediation", "workaround"),
    ("runbook", "playbook"),
    ("procedure", "process", "steps"),
    ("rollback", "revert"),
    ("target", "objective", "goal"),
    ("cadence", "frequency"),
    # config / deploy
    ("config", "configuration", "cfg"),
    ("deploy", "deployment", "release", "rollout"),
    ("production", "prod"),
    ("flag", "toggle"),
    # networking
    ("endpoint", "url"),
    ("path", "route"),
    ("stickiness", "affinity"),
    # cache / credentials
    ("flush", "purge"),
    ("token", "secret", "credential"),
    ("password", "passphrase"),
    ("rotation", "rollover"),
)

# Multi-word spellings folded to one token before tokenizing.
OPS_PHRASES: tuple[tuple[str, str], ...] = (
    ("response time", "responsetime"),
    ("requests per second", "rps"),
    ("request rate", "qps"),
)

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
