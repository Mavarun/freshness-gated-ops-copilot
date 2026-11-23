"""Does a query ask for a credential's *value*? (2026-11-24, protocol: credential_request_protocol.py)

Every hazard gate reads the draft or the evidence. "Paste the slack token for the incident bot" lands
on an incident thread that carries no secret, so it is answered. This reads the question instead:
a credential noun, with no attribute or procedure word and no how / why / when / where / who
opening, is a request for the value. Written from the 40 regression rows that name a credential
and the 24 Nov 24 band rows; the Nov 24 fresh set was not looked at.

The gate that uses it (``credential_request_gate``) only turns an ANSWER into REFUSE_PII, so a
false positive costs an answer, never a leak.
"""

from __future__ import annotations

import re

from ops_copilot.explain import Remediation, RefusalExplanation, finalize

_CRED = re.compile(
    r"\b(tokens?|passwords?|passphrases?|secrets?|credentials?|creds|"
    r"(?:api|access|private|signing|ssh|deploy)\s+keys?|key\s+ids?)\b",
    re.I,
)
# Words that make the question about the credential, not its value.
_ATTRIBUTE = frozenset(
    "ttl lifetime lifespan longevity expiry expiration expire expires expired validity valid timeout "
    "max-age age rotation rotate rotated rotating cycling cycle interval period schedule window policy "
    "owner owns owned contact email phone scope format length procedure runbook revoke revoked "
    "revoking reset renew regenerate leaked leak stored storage store".split()
)
_OPENERS = frozenset({"how", "why", "when", "where", "who"})


def _words(q: str) -> list[str]:
    return re.findall(r"[a-z0-9][a-z0-9'-]*", q.lower())


def is_credential_request(query: str) -> bool:
    """True when ``query`` names a credential and asks for nothing about it but its value."""
    if not _CRED.search(query):
        return False
    words = _words(query)
    if not words or words[0] in _OPENERS:
        return False
    return not any(w in _ATTRIBUTE for w in words)


def credential_explanation(doc_ids: list[str], query: str = "") -> dict:
    """Structured REFUSE_PII explanation for a refused credential request (no values in it)."""
    expl = RefusalExplanation(
        "REFUSE_PII", "pii",
        "the question asks for a credential value; credentials are never answered (values withheld)",
        evidence_doc_ids=list(doc_ids),
        details={"kinds": ["credential_request"], "evidence_secret_kinds": [], "n_matches": 0},
        remediation=[Remediation("use_secret_store", None,
                                 "Fetch the credential from the secret store; ask how to rotate or who owns it instead.")],
    )
    return finalize(expl, context=(query,) if query else ())
