"""PII / secret redaction gate for extractive answers.

Plant emails, phones, AWS-like keys, and Slack tokens in a subset of ops docs.
After an extractive draft is built, scan it:

* Unauthorized PII or any secret in the draft → ``REFUSE_PII``.
* Queries that *explicitly* authorize contact disclosure (keyword allowlist)
  may receive a **masked** email/phone answer (never raw).
* AWS-like keys and Slack tokens **never** authorize — always refuse.

Offline only — regex + simple patterns; no paid LLM.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

# --- detection patterns (synthetic lab probes, not production secrets) ---

EMAIL_RE = re.compile(
    r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"
)
# US-ish and E.164-ish phones; require separators so bare ints do not trip.
PHONE_RE = re.compile(
    r"(?<!\w)(?:\+?1[-.\s]?)?(?:\(?\d{3}\)?[-.\s])\d{3}[-.\s]\d{4}(?!\w)"
)
# AWS access key id shape (AKIA…); example-style lab keys only in corpus.
AWS_KEY_RE = re.compile(r"\bAKIA[0-9A-Z]{16}\b")
# Slack bot/user/app token prefixes used in planted probes.
SLACK_TOKEN_RE = re.compile(r"\bxox[baprs]-[0-9A-Za-z-]{10,}\b")

PII_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("email", EMAIL_RE),
    ("phone", PHONE_RE),
    ("aws_key", AWS_KEY_RE),
    ("slack_token", SLACK_TOKEN_RE),
)

# Secrets never authorize — even if the query names them.
SECRET_KINDS: frozenset[str] = frozenset({"aws_key", "slack_token"})

# Query must match at least one phrase to allow *masked* email/phone disclosure.
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
    # Drop overlaps: keep earlier / longer span.
    kept: list[PiiMatch] = []
    last_end = -1
    for h in hits:
        if h.start < last_end:
            continue
        kept.append(h)
        last_end = h.end
    return tuple(kept)


def mask_email(value: str) -> str:
    """Mask local-part leaving first char + domain: a***@example.com."""
    if "@" not in value:
        return "***"
    local, _, domain = value.partition("@")
    if not local:
        return f"***@{domain}"
    return f"{local[0]}***@{domain}"


def mask_phone(value: str) -> str:
    """Keep last 4 digits only."""
    digits = re.sub(r"\D", "", value)
    tail = digits[-4:] if len(digits) >= 4 else "****"
    return f"***-***-{tail}"


def mask_aws_key(value: str) -> str:
    """Show AKIA prefix only."""
    return "AKIA****************"


def mask_slack_token(value: str) -> str:
    """Show xox* prefix only."""
    prefix = value.split("-", 1)[0] if value else "xox*"
    return f"{prefix}-********"


_MASKERS = {
    "email": mask_email,
    "phone": mask_phone,
    "aws_key": mask_aws_key,
    "slack_token": mask_slack_token,
}


def redact_text(text: str, matches: tuple[PiiMatch, ...] | None = None) -> tuple[str, int]:
    """Replace each match with a kind-specific mask. Returns (redacted, count)."""
    found = matches if matches is not None else detect_pii(text)
    if not found:
        return text, 0
    # Replace from the end so offsets stay valid.
    out = text
    for m in sorted(found, key=lambda x: x.start, reverse=True):
        masker = _MASKERS.get(m.kind, lambda v: "***")
    # NOTE truncated intentionally to test - DO NOT USE
