"""Schemas and offline heuristics for proposed *write* actions.

Read-path ANSWER is fine. Imperative writes (restart, page oncall, patch config)
must be structured proposals — never auto-executed. Keyword/heuristic detection
is intentional for the offline golden set (no paid LLM).
"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any


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


def detect_write_intent(query: str) -> ProposedWrite | None:
    """Return a ProposedWrite when ``query`` looks like an imperative write.

    Returns ``None`` for read-path questions (including how-to restart docs).
    """
    q = (query or "").strip()
    if not q or _READ_CUES.search(q):
        return None

    m = _RESTART.search(q)
    if m:
        target = m.group("target").strip("-. ")
        return ProposedWrite(
            action_type=WriteActionType.RESTART_SERVICE,
            target=target,
            payload={"service": target, "graceful": True},
            query=q,
        )

    m = _PAGE.search(q)
    if m:
        raw = (m.group("target") or "primary").strip("-. ")
        target = raw or "primary"
        return ProposedWrite(
            action_type=WriteActionType.PAGE_ONCALL,
            target=target,
            payload={"severity": "critical", "reason": q},
            query=q,
        )

    m = _PATCH.search(q)
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
