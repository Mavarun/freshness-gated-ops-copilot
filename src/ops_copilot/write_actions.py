"""Schemas and offline heuristics for proposed *write* actions.

Read-path ANSWER is fine. Imperative writes (restart, page oncall, patch config)
must be structured proposals — never auto-executed. Keyword/heuristic detection
is intentional for the offline golden set (no paid LLM).

Detection runs on ``text.normalize_text(query)`` so case, curly quotes, and
trailing punctuation never decide whether a write is proposed. With typo
tolerance on, words of 5+ characters one keyboard slip from a write keyword
(``rrstart``, ``pathc``, ``onclal``) are read as that keyword; inflections
(``restarts``, ``patched``) are left alone so descriptions do not become writes.
"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any

from ops_copilot.lexicon import is_keyboard_typo
from ops_copilot.text import is_identifier, normalize_text


class WriteActionType(str, Enum):
    RESTART_SERVICE = "restart_service"
    PAGE_ONCALL = "page_oncall"
    PATCH_CONFIG = "patch_config"


# How-to / definition reads must not trip the write gate.
_READ_CUES = re.compile(
    r"^\s*(how\s+(do|to|can|should)|what\s+(is|are|does)|where\s+is|"
    r"who\s+is|when\s+(is|does)|why\s+(is|does)|explain|describe)\b",
    re.IGNORECASE,
)

_RESTART = re.compile(
    r"\b(?:please\s+|go\s+ahead\s+and\s+|can\s+you\s+|could\s+you\s+)?"
    r"restart\s+(?:the\s+)?(?P<target>[\w.-]+)",
    re.IGNORECASE,
)
_PAGE = re.compile(
    r"\b(?:please\s+|can\s+you\s+|could\s+you\s+)?"
    r"page\s+(?:the\s+)?on[- ]?call"
    r"(?:\s+for\s+(?:the\s+)?(?P<target>[\w\s.-]+?))?(?:\s+now)?\s*[.!]?\s*$",
    re.IGNORECASE,
)
_PATCH = re.compile(
    r"\b(?:please\s+|can\s+you\s+|could\s+you\s+)?"
    r"patch\s+(?:the\s+)?(?P<target>[\w./:-]+)(?:\s+config)?\b"
    r"(?:\s+(?:to|with)\s+(?P<value>[\w.-]+))?",
    re.IGNORECASE,
)


# Keywords the regexes below key on; typo snapping targets only these.
WRITE_KEYWORDS: tuple[str, ...] = ("restart", "patch", "oncall", "on-call", "config")


def _snap_write_keywords(text: str) -> str:
    out: list[str] = []
    for word in text.split():
        if len(word) >= 5 and word.isalpha() and not is_identifier(word):
            for kw in WRITE_KEYWORDS:
                if word == kw or word.startswith(kw) or kw.startswith(word):
                    break
                if is_keyboard_typo(word, kw):
                    word = kw
                    break
        out.append(word)
    return " ".join(out)


@dataclass
class ProposedWrite:
    """Structured write the agent wants to perform — pending until HITL approve."""

    action_type: WriteActionType
    target: str
    payload: dict[str, Any] = field(default_factory=dict)
    evidence_ids: list[str] = field(default_factory=list)
    query: str = ""

    def as_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["action_type"] = self.action_type.value
        return d


def detect_write_intent(query: str, *, typo_tolerance: bool = True) -> ProposedWrite | None:
    """Return a ProposedWrite when ``query`` looks like an imperative write.

    Returns ``None`` for read-path questions (including how-to restart docs).
    """
    q = (query or "").strip()
    nq = normalize_text(q)
    if not nq or _READ_CUES.search(nq):
        return None
    if typo_tolerance:
        nq = _snap_write_keywords(nq)

    m = _RESTART.search(nq)
    if m:
        target = m.group("target").strip("-. ")
        return ProposedWrite(
            action_type=WriteActionType.RESTART_SERVICE,
            target=target,
            payload={"service": target, "graceful": True},
            query=q,
        )

    m = _PAGE.search(nq)
    if m:
        raw = (m.group("target") or "primary").strip("-. ")
        target = raw or "primary"
        return ProposedWrite(
            action_type=WriteActionType.PAGE_ONCALL,
            target=target,
            payload={"severity": "critical", "reason": q},
            query=q,
        )

    m = _PATCH.search(nq)
    if m:
        target = m.group("target").strip("-. ")
        value = m.group("value")
        payload: dict[str, Any] = {"config_key": target}
        if value:
            payload["value"] = value
        return ProposedWrite(
            action_type=WriteActionType.PATCH_CONFIG,
            target=target,
            payload=payload,
            query=q,
        )

    return None
