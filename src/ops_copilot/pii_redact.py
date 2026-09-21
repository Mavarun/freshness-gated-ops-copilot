"""PII redact helpers and authorize/refuse scan policy.

Builds on ``ops_copilot.pii`` detectors. Secrets never authorize; contact
allowlist queries may receive masked email/phone answers.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from ops_copilot.pii import (
    AUTHORIZE_CONTACT_PHRASES,
    PiiMatch,
    SECRET_KINDS,
    detect_pii,
)


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
    out = text
    for m in sorted(found, key=lambda x: x.start, reverse=True):
        masker = _MASKERS.get(m.kind, lambda v: "***")
        out = out[: m.start] + masker(m.value) + out[m.end :]
    return out, len(found)


def query_authorizes_contact(query: str) -> bool:
    """True when the query explicitly asks for a contact email/phone (allowlist)."""
    q = (query or "").lower()
    return any(phrase in q for phrase in AUTHORIZE_CONTACT_PHRASES)


@dataclass
class PiiScanResult:
    """Outcome of scanning an answer draft for PII/secrets + policy action."""

    matches: tuple[PiiMatch, ...] = ()
    authorized: bool = False
    action: str = "pass"  # pass | redact | refuse
    redacted_text: str = ""
    redactions_count: int = 0

    @property
    def pii_detected(self) -> bool:
        return bool(self.matches)

    @property
    def has_secret(self) -> bool:
        return any(m.is_secret for m in self.matches)

    @property
    def should_refuse(self) -> bool:
        return self.action == "refuse"

    def as_dict(self) -> dict:
        return {
            "pii_detected": self.pii_detected,
            "redactions_count": self.redactions_count,
            "action": self.action,
            "authorized": self.authorized,
            "kinds": [m.kind for m in self.matches],
            "has_secret": self.has_secret,
            "n_matches": len(self.matches),
        }


def scan_answer_pii(answer: str, query: str) -> PiiScanResult:
    """Detect PII in ``answer`` and decide pass / redact / refuse.

    Policy:
    - No matches → pass.
    - Any secret (aws_key, slack_token) → refuse (never authorize).
    - Email/phone + query authorize allowlist → redact (mask) and allow ANSWER.
    - Email/phone without authorize → refuse.
    """
    matches = detect_pii(answer)
    if not matches:
        return PiiScanResult(
            matches=(),
            authorized=False,
            action="pass",
            redacted_text=answer,
            redactions_count=0,
        )

    authorized = query_authorizes_contact(query)
    has_secret = any(m.is_secret for m in matches)

    if has_secret or not authorized:
        redacted, n = redact_text(answer, matches)
        return PiiScanResult(
            matches=matches,
            authorized=authorized and not has_secret,
            action="refuse",
            redacted_text=redacted,
            redactions_count=n,
        )

    redacted, n = redact_text(answer, matches)
    return PiiScanResult(
        matches=matches,
        authorized=True,
        action="redact",
        redacted_text=redacted,
        redactions_count=n,
    )


def pii_detection_metrics(cases: list[dict]) -> dict[str, float | int]:
    """Precision/recall for PII detection over labeled golden cases."""
    labeled = [c for c in cases if "expect_pii" in c]
    if not labeled:
        return {
            "n_labeled": 0,
            "pii_precision": 0.0,
            "pii_recall": 0.0,
            "pii_f1": 0.0,
            "true_positives": 0,
            "false_positives": 0,
            "false_negatives": 0,
            "true_negatives": 0,
        }
    tp = fp = fn = tn = 0
    for c in labeled:
        expect = bool(c["expect_pii"])
        actual = bool(c.get("actual_pii", False))
        if expect and actual:
            tp += 1
        elif not expect and actual:
            fp += 1
        elif expect and not actual:
            fn += 1
        else:
            tn += 1
    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = (
        2 * precision * recall / (precision + recall)
        if (precision + recall)
        else 0.0
    )
    return {
        "n_labeled": len(labeled),
        "pii_precision": round(precision, 4),
        "pii_recall": round(recall, 4),
        "pii_f1": round(f1, 4),
        "true_positives": tp,
        "false_positives": fp,
        "false_negatives": fn,
        "true_negatives": tn,
    }
