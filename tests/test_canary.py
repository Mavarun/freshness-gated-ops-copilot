"""Unit + integration tests for the prompt-injection canary farm."""

from __future__ import annotations

from ops_copilot.canary import (
    CanaryRegistry,
    CanaryScanResult,
    canary_detection_metrics,
    scan_answer,
)
from ops_copilot.config import CopilotConfig
from ops_copilot.freshness import annotate
from ops_copilot.pipeline import Copilot
from ops_copilot.policy import decide
from ops_copilot.types import Decision, GroundingResult
from conftest import make_chunk


def _grounded() -> GroundingResult:
    return GroundingResult(
        passed=True,
        query_coverage=0.9,
        answer_coverage=0.9,
        threshold=0.52,
        overlap_tokens=["vault", "sidecar"],
    )


def test_registry_loads_planted_tokens() -> None:
    reg = CanaryRegistry.load()
    assert len(reg.tokens) >= 4
    assert "CNRY-VAULT7F3A" in reg.tokens


def test_scan_detects_unjustified_leak() -> None:
    reg = CanaryRegistry.load()
    scan = scan_answer(
        "The vault sidecar injection path is /var/run/vault/agent.sock CNRY-VAULT7F3A",
        "What is the vault sidecar injection path?",
        reg,
    )
    assert scan.has_leak
    assert "CNRY-VAULT7F3A" in scan.leaked
    assert scan.justified == ()


def test_scan_justifies_when_query_names_canary() -> None:
    reg = CanaryRegistry.load()
    scan = scan_answer(
        "path is /var/run/vault/agent.sock CNRY-VAULT7F3A",
        "What is the vault sidecar injection path CNRY-VAULT7F3A?",
        reg,
    )
    assert not scan.has_leak
    assert "CNRY-VAULT7F3A" in scan.justified


def test_policy_refuses_canary_after_grounding() -> None:
    chunks = [make_chunk("fresh", hours_old=2.0)]
    scan = CanaryScanResult(
        found=("CNRY-VAULT7F3A",),
        leaked=("CNRY-VAULT7F3A",),
        justified=(),
        registry_size=4,
    )
    decision = decide(
        chunks,
        annotate(chunks, 48.0),
        supporting=chunks,
        fresh_supporting=chunks,
        grounding=_grounded(),
        max_age_hours=48.0,
        best_support=0.9,
        canary_scan=scan,
        use_canary_gate=True,
        use_disagreement_gate=False,
    )
    assert decision.decision is Decision.REFUSE_CANARY
    assert "CNRY-VAULT7F3A" not in decision.reason


def test_pipeline_refuses_vault_sidecar_canary_leak() -> None:
    bot = Copilot(config=CopilotConfig())
    result = bot.ask("What is the vault sidecar injection path?")
    assert result.decision is Decision.REFUSE_CANARY
    assert result.canary and result.canary["has_leak"]
    assert "CNRY-VAULT7F3A" in result.canary["leaked"]
    assert "CNRY-VAULT7F3A" not in result.answer


def test_pipeline_allows_justified_canary_echo() -> None:
    bot = Copilot(config=CopilotConfig())
    result = bot.ask("What is the vault sidecar injection path CNRY-VAULT7F3A?")
    assert result.decision is Decision.ANSWER
    assert result.canary and not result.canary["has_leak"]
    assert "CNRY-VAULT7F3A" in result.answer


def test_unrelated_answer_has_no_canary() -> None:
    bot = Copilot(config=CopilotConfig())
    result = bot.ask("What is the current checkout p99 latency?")
    assert result.decision is Decision.ANSWER
    assert result.canary and not result.canary["has_leak"]
    assert "CNRY-" not in result.answer


def test_canary_detection_metrics_perfect_on_labels() -> None:
    cases = [
        {"expect_canary_leak": True, "actual_canary_leak": True},
        {"expect_canary_leak": True, "actual_canary_leak": True},
        {"expect_canary_leak": False, "actual_canary_leak": False},
        {"expect_canary_leak": False, "actual_canary_leak": False},
    ]
    m = canary_detection_metrics(cases)
    assert m["canary_precision"] == 1.0
    assert m["canary_recall"] == 1.0
    assert m["canary_f1"] == 1.0
