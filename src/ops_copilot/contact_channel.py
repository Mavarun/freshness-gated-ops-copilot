"""Contact-channel authorization for the PII gate (2026-11-21).

The shipped PII gate authorizes a masked email / phone answer only when the query
contains one of ten fixed phrases (``pii.AUTHORIZE_CONTACT_PHRASES``): "contact
email" opens it, but "contact inbox", "contact mailbox" or "liaison email" do not, so
those questions are refused as REFUSE_PII even though they ask for the same value.

This module replaces phrase matching with two separate checks, both written from
the gate's own definitions rather than from eval rows:

1. **Query side, which channel is asked for.** ``requested_kinds(query)`` maps
   channel nouns to the detector kinds in ``pii.py`` (``email``, ``phone``). The
   nouns are the everyday names of those two kinds. Bare ``address`` and ``number``
   are left out on purpose: "admin address" and "port number" are not contact
   requests.
2. **Evidence side, whether the page offers the value as a contact.** A match is
   *designated* when its own sentence in the draft carries one of the role words
   the old allowlist already used (contact, on-call, pager, notify). "The rotation
   contact email is X" is designated; "the directory lists X as the primary owner
   mailbox for break-glass" is not, so asking for the owner mailbox still refuses.

``authorizes(query, draft, matches)`` is True only when the query asks for a
channel of a kind that is in the draft and every email / phone match sits in a
designated sentence. Secrets never authorize (``scan_answer_pii`` refuses them
before this is consulted). Authorized answers are still masked.
"""

from __future__ import annotations

import re
from collections.abc import Sequence

from ops_copilot.pii import PiiMatch
from ops_copilot.text import normalize_text

# Channel nouns per detector kind. Hyphenated forms are matched whole and by parts.
EMAIL_CHANNEL: frozenset[str] = frozenset(
    {"email", "emails", "e-mail", "e-mails", "mail", "mailbox", "mailboxes", "inbox", "inboxes", "mail-address"}
)
PHONE_CHANNEL: frozenset[str] = frozenset(
    {"phone", "phones", "telephone", "phone-number", "mobile", "cellphone"}
)
CHANNEL_KINDS: dict[str, frozenset[str]] = {"email": EMAIL_CHANNEL, "phone": PHONE_CHANNEL}

# Role words of the old allowlist phrases ("contact email", "oncall email", "pager
# email", "notify email", ...). "rotation" is left out: the owner-directory page is a
# rotation page too, and its mailbox is not offered as a contact.
DESIGNATION_WORDS: frozenset[str] = frozenset(
    {"contact", "contacts", "oncall", "on-call", "pager", "notify", "notification", "notifications"}
)

_WORD = re.compile(r"[a-z0-9][a-z0-9-]*")
_SENTENCE_END = re.compile(r"[.!?](?=\s|$)")


def _words(text: str) -> set[str]:
    out: set[str] = set()
    for w in _WORD.findall(normalize_text(text)):
        out.add(w)
        if "-" in w:
            out.update(p for p in w.split("-") if p)
    return out


def requested_kinds(query: str) -> frozenset[str]:
    """Detector kinds (``email`` / ``phone``) whose channel the query names."""
    words = _words(query)
    return frozenset(kind for kind, nouns in CHANNEL_KINDS.items() if words & nouns)


def _sentence_of(text: str, start: int, end: int) -> str:
    """The sentence of ``text`` that holds the span; a '.' inside an email is not an end."""
    left = 0
    for m in _SENTENCE_END.finditer(text):
        if m.end() <= start:
            left = m.end()
        elif m.start() >= end:
            return text[left : m.end()]
    return text[left:]


def is_designated(text: str, match: PiiMatch) -> bool:
    """True when the match's own sentence offers it as a contact (a role word is present)."""
    return bool(_words(_sentence_of(text, match.start, match.end)) & DESIGNATION_WORDS)


def authorizes(query: str, draft: str, matches: Sequence[PiiMatch]) -> bool:
    """Contact-channel authorization for a draft with email / phone matches (no secrets)."""
    if not matches or any(m.is_secret for m in matches):
        return False
    asked = requested_kinds(query)
    if not asked & {m.kind for m in matches}:
        return False
    return all(is_designated(draft, m) for m in matches)
