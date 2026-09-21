"""PII / secret detector patterns (email, phone, AWS-like keys, Slack tokens).

Offline regex probes for a post-answer scanner. Redaction helpers and the
authorize/refuse policy land in follow-up commits.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

EMAIL_RE = re.compile(
    r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"
)
PHONE_RE = re.compile(
    r"(?<!\w)(?:\+?1[-.\s]?)?(?:\(?\d{3}\)?[-.\s])\d{3}[-.\s]\d{4}(?!\w)"
)
AWS_KEY_RE = re.compile(r"\bAKIA[0-9A-Z]{16}\b")
SLACK_TOKEN_RE = re.compile(r"\bxox[baprs]-[0-9A-Za-z-]{10,}\b")

PII_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("email", EMAIL_RE),
    ("phone", PHONE_RE),
    ("aws_key", AWS_KEY_RE),
    ("slack_token", SLACK_TOKEN_RE),
)

SECRET_KINDS: frozenset[str] = frozenset({"aws_key", "slack_token"})

AUTHORIZE_CONTACT_PHRASES: tuple[str, ...] = (
    "rotation contact email",
    "contact email",
    "rotation email",
    "oncall email",
    "on-call email",
    "pager email",
    "notify email",
    "email address",
    "phone number for rotation",
    "rotation contact phone",
)


@dataclass(frozen=True)
class PiiMatch:
    """One PII/secret span found in text."""

    kind: str
    value: str
    start: int
    end: int

    @property
    def is_secret(self) -> bool:
        return self.kind in SECRET_KINDS


def detect_pii(text: str) -> tuple[PiiMatch, ...]:
    """Return all PII/secret matches in ``text`` (stable order by start offset)."""
    if not text:
        return ()
    hits: list[PiiMatch] = []
    for kind, pattern in PII_PATTERNS:
        for m in pattern.finditer(text):
            hits.append(
                PiiMatch(kind=kind, value=m.group(0), start=m.start(), end=m.end())
            )
    hits.sort(key=lambda h: (h.start, h.end, h.kind))
    kept: list[PiiMatch] = []
    last_end = -1
    for h in hits:
        if h.start < last_end:
            continue
        kept.append(h)
        last_end = h.end
    return tuple(kept)
