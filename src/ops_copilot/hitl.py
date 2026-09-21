"""Human-in-the-loop ledger for proposed write actions.

Audit story: propose → approve|reject with actor + timestamp.
Execute stub runs **only** after approve. Rejected writes never execute.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from ops_copilot.write_actions import ProposedWrite


class WriteStatus(str, Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    EXECUTED = "EXECUTED"


@dataclass
class AuditEvent:
    event: str
    actor: str
    timestamp: str
    detail: str = ""

    def as_dict(self) -> dict[str, Any]:
        return {
            "event": self.event,
            "actor": self.actor,
            "timestamp": self.timestamp,
            "detail": self.detail,
        }


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class WriteRecord:
    write_id: str
    proposal: ProposedWrite
    status: WriteStatus = WriteStatus.PENDING
    audit: list[AuditEvent] = field(default_factory=list)
    executed: bool = False
    execution_result: dict[str, Any] | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "write_id": self.write_id,
            "status": self.status.value,
            "proposal": self.proposal.as_dict(),
            "audit": [a.as_dict() for a in self.audit],
            "executed": self.executed,
            "execution_result": self.execution_result,
        }


class HitlWriteLedger:
    """In-memory propose / approve / reject / execute-stub ledger (single-process)."""

    def __init__(self) -> None:
        self._records: dict[str, WriteRecord] = {}

    def propose(
        self,
        proposal: ProposedWrite,
        *,
        actor: str = "copilot",
        write_id: str | None = None,
        evidence_ids: list[str] | None = None,
    ) -> WriteRecord:
        if evidence_ids is not None:
            proposal.evidence_ids = list(evidence_ids)
        wid = write_id or f"wrt_{uuid.uuid4().hex[:12]}"
        record = WriteRecord(
            write_id=wid,
            proposal=proposal,
            status=WriteStatus.PENDING,
            audit=[
                AuditEvent(
                    event="propose",
                    actor=actor,
                    timestamp=_now_iso(),
                    detail=f"{proposal.action_type.value}:{proposal.target}",
                )
            ],
        )
        self._records[wid] = record
        return record

    def get(self, write_id: str) -> WriteRecord | None:
        return self._records.get(write_id)

    def list_pending(self) -> list[WriteRecord]:
        return [
            r
            for r in self._records.values()
            if r.status is WriteStatus.PENDING
        ]

    def approve(self, write_id: str, *, actor: str) -> WriteRecord:
        record = self._require(write_id)
        if record.status is WriteStatus.REJECTED:
            raise ValueError(f"write {write_id} was rejected; cannot approve")
        if record.status is WriteStatus.EXECUTED:
            return record
        if record.status is WriteStatus.PENDING:
            record.status = WriteStatus.APPROVED
            record.audit.append(
                AuditEvent(
                    event="approve",
                    actor=actor,
                    timestamp=_now_iso(),
                    detail="human approved; executing stub",
                )
            )
        return self.execute_stub(write_id, actor=actor)

    def reject(self, write_id: str, *, actor: str, reason: str = "") -> WriteRecord:
        record = self._require(write_id)
        if record.executed:
            raise ValueError(f"write {write_id} already executed; cannot reject")
        if record.status is WriteStatus.REJECTED:
            return record
        record.status = WriteStatus.REJECTED
        record.audit.append(
            AuditEvent(
                event="reject",
                actor=actor,
                timestamp=_now_iso(),
                detail=reason or "human rejected; will not execute",
            )
        )
        # Hard invariant: rejected writes never execute.
        record.executed = False
        record.execution_result = None
        return record

    def execute_stub(self, write_id: str, *, actor: str = "system") -> WriteRecord:
        """Run the offline execute stub — **only** when status is APPROVED."""
        record = self._require(write_id)
        if record.status is WriteStatus.REJECTED:
            raise PermissionError(
                f"write {write_id} is REJECTED; execute stub refused"
            )
        if record.status is WriteStatus.PENDING:
            raise PermissionError(
                f"write {write_id} is still PENDING; approve required before execute"
            )
        if record.status is WriteStatus.EXECUTED and record.executed:
            return record
        if record.status is not WriteStatus.APPROVED:
            raise PermissionError(
                f"write {write_id} status={record.status.value}; cannot execute"
            )
        prop = record.proposal
        record.execution_result = {
            "ok": True,
            "stub": True,
            "action_type": prop.action_type.value,
            "target": prop.target,
            "payload": dict(prop.payload),
            "message": (
                f"STUB executed {prop.action_type.value} on {prop.target} "
                f"(no real side effects)"
            ),
        }
        record.executed = True
        record.status = WriteStatus.EXECUTED
        record.audit.append(
            AuditEvent(
                event="execute_stub",
                actor=actor,
                timestamp=_now_iso(),
                detail=record.execution_result["message"],
            )
        )
        return record

    def reset(self) -> None:
        self._records.clear()

    def as_dict(self) -> dict[str, Any]:
        return {wid: r.as_dict() for wid, r in self._records.items()}

    def _require(self, write_id: str) -> WriteRecord:
        record = self._records.get(write_id)
        if record is None:
            raise KeyError(f"unknown write_id: {write_id}")
        return record
