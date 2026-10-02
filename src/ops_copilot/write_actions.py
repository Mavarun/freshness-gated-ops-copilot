"""Structured proposals for *write* actions, and the gate entry point.

Read-path ANSWER is fine. Imperative writes (restart, scale, roll back, page,
flip a flag, rotate a secret, patch a setting, clear a cache) must be
structured proposals, never auto-executed (``hitl.HitlWriteLedger``).

Until PR #12 detection was three keyword regexes. It is now the structured
parser in ``write_intent`` (action ontology ``write_ontology``, target
registry ``write_targets``, clause mood ``write_mood``, optional embedding
prototypes ``write_prototypes``). ``detect_write_intent`` keeps its old
contract: a ``ProposedWrite`` for a confident write, else ``None``; use
``classify_write_intent`` to also see ambiguous writes, which the policy
refuses with ``REFUSE_AMBIGUOUS_WRITE``.

A proposal now carries the parse: ``confidence`` and ``parse`` (mood, verb,
verb source, target kind and source, prototype match when one was used).
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from ops_copilot.write_intent import (
    PROPOSE,
    WriteIntent,
    classify_write_intent,
)
from ops_copilot.write_ontology import WriteActionType

__all__ = [
    "ProposedWrite",
    "WriteActionType",
    "classify_write_intent",
    "detect_write_intent",
    "proposal_from_intent",
]


@dataclass
class ProposedWrite:
    """Structured write the agent wants to perform: pending until HITL approve."""

    action_type: WriteActionType
    target: str
    payload: dict[str, Any] = field(default_factory=dict)
    evidence_ids: list[str] = field(default_factory=list)
    query: str = ""
    confidence: float = 1.0
    parse: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["action_type"] = self.action_type.value
        d["confidence"] = round(self.confidence, 3)
        return d


def proposal_from_intent(intent: WriteIntent) -> ProposedWrite | None:
    """The PENDING proposal for a ``propose`` intent (None otherwise)."""
    if intent.status != PROPOSE or intent.action is None or intent.target is None:
        return None
    return ProposedWrite(
        action_type=intent.action,
        target=intent.target.name,
        payload=dict(intent.payload),
        query=intent.query,
        confidence=intent.confidence,
        parse=intent.parse_dict(),
    )


def detect_write_intent(
    query: str,
    *,
    typo_tolerance: bool = True,
    synonyms: bool = True,  # noqa: ARG001 - kept for the PR #12 signature
    mood_detection: bool = True,
) -> ProposedWrite | None:
    """Return a ProposedWrite when ``query`` is a confident imperative write.

    Returns ``None`` for reads (including how-to restart docs) and for
    ambiguous writes; ``classify_write_intent`` tells those apart.
    """
    intent = classify_write_intent(query, typo_tolerance=typo_tolerance, mood_detection=mood_detection)
    return proposal_from_intent(intent)
