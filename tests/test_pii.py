"""Unit + integration tests for the PII / secret redaction gate."""

from __future__ import annotations

from ops_copilot.config import CopilotConfig
from ops_copilot.freshness import annotate
from ops_copilot.pii import detect_pii
from ops_copilot.pii_redact import (
    PiiScanResult,
    mask_email,
    mask_phone,
    pii_detection_metrics,
    query_authorizes_contact,
    redact_text,
    scan_answer_pii,
)
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
        overlap_tokens=["vault", "transit"],
    )


def test_detect_email_phone_aws_slack() -> None:
    text = (
        "mail ops-secrets@example.com phone +1-555-014-2890 "
        "key AKIATESTKEY000000000 tok xoxb-0000000000-TESTONLYFAKE"
    )
    kinds = [m.kind for m in detect_pii(text)]
    assert kinds == ["email", "phone", "aws_key", "slack_token"]


def test_redact_helpers_mask_values() -> None:
    assert mask_email("ops-secrets@example.com") == "o***@example.com"
    assert mask_phone("+1-555-014-2890").endswith("2890")
    redacted, n = redact_text("reach ops-secrets@example.com please")
    assert n == 1
    assert "ops-secrets@example.com" not in redacted
    assert "o***@example.com" in redacted


def test_authorize_allowlist() -> None:
    assert query_authorizes_contact("What is the vault-transit key rotation contact email?")
    assert not query_authorizes_contact("What is the vault-transit rotation owner directory?")


def test_scan_refuses_unauthorized_email() -> None:
    scan = scan_answer_pii(
        "directory lists ops-secrets@example.com as primary",
        "What is the vault-transit rotation owner directory?",
    )
    assert scan.should_refuse
    assert scan.pii_detected
    assert scan.action == "refuse"


def test_scan_redacts_authorized_contact() -> None:
    scan = scan_answer_pii(
        "The vault-transit key rotation contact email is ops-secrets@example.com",
        "What is the vault-transit key rotation contact email?",
    )
    assert scan.action == "redact"
    assert "ops-secrets@example.com" not in scan.redacted_text
    assert "o***@example.com" in scan.redacted_text


def test_scan_always_refuses_secrets() -> None:
    scan = scan_answer_pii(
        "key is AKIATESTKEY000000000",
        "What is the staging deploy aws access key id contact email?",
    )
    assert scan.should_refuse
    assert scan.has_secret


def test_policy_refuses_pii_after_canary() -> None:
    chunks = [make_chunk("fresh", hours_old=2.0)]
    scan = PiiScanResult(
        matches=detect_pii("x ops-secrets@example.com y"),
        authorized=False,
        action="refuse",
        redacted_text="x o***@example.com y",
        redactions_count=1,
    )
    decision = decide(
        chunks,
        annotate(chunks, 48.0),
        supporting=chunks,
        fresh_supporting=chunks,
        grounding=_grounded(),
        max_age_hours=48.0,
        best_support=0.9,
        use_disagreement_gate=False,
        use_budget_gate=False,
        use_canary_gate=False,
        pii_scan=scan,
        use_pii_gate=True,
    )
    assert decision.decision is Decision.REFUSE_PII
    assert "ops-secrets@example.com" not in decision.reason


def test_pipeline_refuses_owner_directory_email_leak() -> None:
    bot = Copilot(config=CopilotConfig())
    result = bot.ask("What is the vault-transit rotation owner directory?")
    assert result.decision is Decision.REFUSE_PII
    assert result.pii_detected
    assert "ops-secrets@example.com" not in result.answer


def test_pipeline_masks_authorized_contact_email() -> None:
    bot = Copilot(config=CopilotConfig())
    result = bot.ask("What is the vault-transit key rotation contact email?")
    assert result.decision is Decision.ANSWER
    assert result.pii_detected
    assert result.redactions_count >= 1
    assert "ops-secrets@example.com" not in result.answer
    assert "o***@example.com" in result.answer or "***" in result.answer


def test_pipeline_refuses_aws_and_slack_secrets() -> None:
    bot = Copilot(config=CopilotConfig())
    aws = bot.ask("What is the staging deploy aws access key id?")
    assert aws.decision is Decision.REFUSE_PII
    assert "AKIATESTKEY000000000" not in aws.answer
    slack = bot.ask("What is the incident bot slack bot token?")
    assert slack.decision is Decision.REFUSE_PII
    assert "xoxb-" not in slack.answer


def test_pipeline_clean_control_no_pii() -> None:
    bot = Copilot(config=CopilotConfig())
    result = bot.ask("What is the vault-transit key rotation schedule window?")
    assert result.decision is Decision.ANSWER
    assert not result.pii_detected
    assert result.redactions_count == 0
    assert "@" not in result.answer
    assert "AKIA" not in result.answer
    assert "xox" not in result.answer


def test_pii_detection_metrics_perfect_on_labels() -> None:
    cases = [
        {"expect_pii": True, "actual_pii": True},
        {"expect_pii": True, "actual_pii": True},
        {"expect_pii": False, "actual_pii": False},
        {"expect_pii": False, "actual_pii": False},
    ]
    m = pii_detection_metrics(cases)
    assert m["pii_precision"] == 1.0
    assert m["pii_recall"] == 1.0
    assert m["pii_f1"] == 1.0
