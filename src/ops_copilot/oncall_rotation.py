"""The current on-call rotation, read from the corpus, as the default page recipient.

PR #13 took the ``for ...`` phrase of a page as its *target* ("page the oncall
for the payments outage" -> target "payments outage"), so a proposal named
an incident, not a person or pager to wake. A page is now addressed to a
recipient, and the incident phrase moves to ``payload["context"]``.

When the request only says *the* on-call ("page the oncall", "page the
on-duty", "page the primary"), the recipient is resolved explicitly from the
corpus: the newest document titled as an on-call rotation that names pagers
in the form ``Primary ... (pager <id>)`` / ``Secondary ... (pager <id>)``
(``wiki_oncall_now`` in the committed corpus: primary ``checkout-primary``,
secondary ``checkout-secondary``). Only pager ids are kept; the people's
names in that page never enter a proposal.

The default is only used while the rotation page itself is fresh under its
source SLA; a stale rotation (or none) means the page needs a named
recipient and the write gate asks for one (REFUSE_AMBIGUOUS_WRITE).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime
from functools import lru_cache
from typing import Callable, Iterable

from ops_copilot.types import Document

_ROTATION_TITLE = re.compile(r"\bon-?call\b.*\brotation\b|\brotation\b.*\bon-?call\b", re.IGNORECASE)
_PAGER = re.compile(
    r"\b(?P<role>primary|secondary)\b[^.()]{0,80}?\(pager\s+(?P<pager>[a-z0-9][a-z0-9-]*[a-z0-9])\)",
    re.IGNORECASE,
)
# Generic page objects and the rotation role each one means.
ROLE_WORDS: dict[str, str] = {
    "oncall": "primary",
    "on-call": "primary",
    "onduty": "primary",
    "on-duty": "primary",
    "pager": "primary",
    "primary": "primary",
    "lead": "primary",
    "secondary": "secondary",
}


@dataclass(frozen=True)
class OncallRotation:
    """Role -> pager id from one rotation document, with its freshness."""

    doc_id: str
    source_system: str
    updated_at: datetime
    pagers: dict[str, str] = field(default_factory=dict)
    age_hours: float | None = None
    sla_hours: float | None = None

    @property
    def fresh(self) -> bool:
        if self.age_hours is None or self.sla_hours is None:
            return True
        return self.age_hours <= self.sla_hours

    def pager_for(self, role: str) -> str | None:
        return self.pagers.get(role) if self.fresh else None

    def as_dict(self) -> dict:
        return {
            "doc_id": self.doc_id,
            "source_system": self.source_system,
            "pagers": dict(self.pagers),
            "age_hours": None if self.age_hours is None else round(self.age_hours, 1),
            "sla_hours": self.sla_hours,
            "fresh": self.fresh,
        }


def rotation_from_docs(
    docs: Iterable[Document],
    *,
    now: datetime | None = None,
    sla_for: Callable[[str], float] | None = None,
) -> OncallRotation | None:
    """The newest on-call rotation page that names a primary pager (or None)."""
    best: OncallRotation | None = None
    for doc in docs:
        if not _ROTATION_TITLE.search(doc.title or ""):
            continue
        pagers: dict[str, str] = {}
        for m in _PAGER.finditer(doc.body or ""):
            pagers.setdefault(m.group("role").lower(), m.group("pager").lower())
        if "primary" not in pagers:
            continue
        if best is None or doc.updated_at > best.updated_at:
            age = (now - doc.updated_at).total_seconds() / 3600.0 if now is not None else None
            sla = float(sla_for(doc.source_system)) if sla_for is not None else None
            best = OncallRotation(doc.doc_id, doc.source_system, doc.updated_at, pagers, age, sla)
    return best


@lru_cache(maxsize=1)
def default_rotation() -> OncallRotation | None:
    """Rotation of the committed corpus at the frozen eval clock, per-source SLAs."""
    from ops_copilot.config import parse_clock
    from ops_copilot.corpus import load_documents
    from ops_copilot.source_slas import load_source_slas

    table = load_source_slas(None)
    return rotation_from_docs(load_documents(None), now=parse_clock(None), sla_for=table.max_age_hours)
