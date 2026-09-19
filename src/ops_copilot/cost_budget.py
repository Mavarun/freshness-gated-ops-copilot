"""Per-session cost accumulator for the hard session budget gate.

Traces already expose ``approx_cost_units``. Production agents need a hard
ceiling: once a session would exceed ``session_budget_cost_units``, policy
emits ``REFUSE_BUDGET`` before answering — independently of freshness or
disagreement.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class SessionCostLedger:
    """In-memory spent units keyed by ``session_id`` (single-process demo)."""

    _spent: dict[str, float] = field(default_factory=dict)

    def spent(self, session_id: str | None) -> float:
        if not session_id:
            return 0.0
        return float(self._spent.get(session_id, 0.0))

    def would_exceed(
        self,
        session_id: str | None,
        request_cost: float,
        budget: float,
    ) -> bool:
        """True when ``session_id`` is set and spent + request would clear budget."""
        if not session_id:
            return False
        return self.spent(session_id) + float(request_cost) > float(budget)

    def record(self, session_id: str | None, cost: float) -> float:
        """Add ``cost`` to the session and return the new total (0 if no session)."""
        if not session_id:
            return 0.0
        total = self.spent(session_id) + float(cost)
        self._spent[session_id] = total
        return total

    def seed(self, session_id: str, amount: float) -> None:
        """Set absolute spent for eval traps / tests."""
        if not session_id:
            raise ValueError("session_id required to seed ledger")
        self._spent[session_id] = float(amount)

    def reset(self, session_id: str | None = None) -> None:
        if session_id is None:
            self._spent.clear()
        elif session_id in self._spent:
            del self._spent[session_id]

    def as_dict(self) -> dict[str, float]:
        return {k: round(v, 4) for k, v in self._spent.items()}
