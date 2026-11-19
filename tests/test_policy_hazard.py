"""hazard_decision: the canary / PII steps of decide(), split out on 2026-11-20."""

from __future__ import annotations

from types import SimpleNamespace

from ops_copilot.types import Decision
from ops_copilot.policy import hazard_decision


def _canary(leaked=("CANARY-X",)):
    return SimpleNamespace(has_leak=bool(leaked), leaked=list(leaked), registry_size=4)


def _pii(kinds=("slack_token",), quarantined=()):
    matches = [SimpleNamespace(kind=k) for k in kinds]
    return SimpleNamespace(
        should_refuse=bool(kinds or quarantined),
        matches=matches,
        redactions_count=len(matches),
        evidence_secret_kinds=list(quarantined),
    )


def test_clean_scans_give_none() -> None:
    assert hazard_decision(_canary(()), SimpleNamespace(should_refuse=False)) is None
    assert hazard_decision(None, None) is None


def test_canary_beats_pii() -> None:
    d = hazard_decision(_canary(), _pii())
    assert d is not None and d.decision is Decision.REFUSE_CANARY
    assert "CANARY-X" not in d.reason


def test_pii_draft_and_quarantine_reasons() -> None:
    d = hazard_decision(_canary(()), _pii())
    assert d.decision is Decision.REFUSE_PII and "slack_token" in d.reason
    q = hazard_decision(None, _pii(kinds=(), quarantined=("private_key",)))
    assert q.decision is Decision.REFUSE_PII and "draft omitted" in q.reason


def test_gate_switches_are_respected() -> None:
    assert hazard_decision(_canary(), None, use_canary_gate=False) is None
    assert hazard_decision(None, _pii(), use_pii_gate=False) is None
