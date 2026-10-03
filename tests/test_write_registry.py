"""Registry-required targets, did-you-mean suggestions and page recipients."""

from __future__ import annotations

from dataclasses import replace

import pytest

from ops_copilot import Copilot
from ops_copilot.oncall_rotation import default_rotation
from ops_copilot.types import Decision
from ops_copilot.write_intent import AMBIGUOUS, PROPOSE, classify_write_intent
from ops_copilot.write_targets import default_registry, suggest_targets


@pytest.mark.parametrize(
    "query, suggestion",
    [
        ("Restart chekout-api", "checkout-api"),
        ("Scale payment-api to 4 replicas", "payments-api"),
        ("Rotate the vault-transt key", "vault-transit"),
    ],
)
def test_misspelled_target_is_refused_with_did_you_mean(query, suggestion) -> None:
    it = classify_write_intent(query)
    assert it.status == AMBIGUOUS and it.reason_code == "unregistered_target"
    assert it.suggestions[0] == suggestion
    assert "did you mean" in it.reason


def test_unregistered_target_is_no_longer_accepted() -> None:
    # PR #13 proposed "restart billing-api" at confidence 0.85.
    it = classify_write_intent("Restart billing-api")
    assert it.status == AMBIGUOUS and it.reason_code == "unregistered_target"
    assert it.suggestions == []  # nothing close: no guess


def test_registry_off_restores_the_old_behaviour() -> None:
    it = classify_write_intent("Restart billing-api", require_registered=False)
    assert it.status == PROPOSE and it.target.name == "billing-api"


def test_suggestions_respect_the_action_kinds() -> None:
    reg = default_registry()
    assert suggest_targets("chekout-api", reg, ("service",)) == ["checkout-api"]
    assert "checkout-cache" not in suggest_targets("checkout-cach", reg, ("recipient",))
    assert suggest_targets("zzzz-nothing", reg) == []


def test_page_with_named_recipient_keeps_the_for_phrase_as_context() -> None:
    it = classify_write_intent("Page checkout-primary for the INC-4821 latency spike")
    assert it.status == PROPOSE and it.target.name == "checkout-primary"
    assert it.payload["recipient_source"] == "registry"
    assert "inc-4821" in it.payload["context"]


def test_generic_page_defaults_to_the_rotation_primary() -> None:
    rot = default_rotation()
    assert rot is not None and rot.doc_id == "wiki_oncall_now" and rot.fresh
    it = classify_write_intent("Page the oncall for the payments outage")
    assert it.status == PROPOSE
    assert it.target.name == rot.pagers["primary"] == "checkout-primary"
    assert it.payload["recipient_source"] == "oncall_rotation"
    assert it.payload["rotation_doc"] == "wiki_oncall_now"
    assert it.payload["context"] == "payments outage"  # never the target


def test_secondary_role_and_typo_role() -> None:
    assert classify_write_intent("Page the secondary").target.name == "checkout-secondary"
    assert classify_write_intent("Page the onclal now").target.name == "checkout-primary"


@pytest.mark.parametrize("query", ["Page for the payments outage", "Page someone about the checkout latency"])
def test_page_without_recipient_asks_and_suggests_primary(query) -> None:
    it = classify_write_intent(query)
    assert it.status == AMBIGUOUS and it.reason_code == "no_recipient"
    assert it.suggestions == ["checkout-primary"]


def test_stale_rotation_is_not_used_as_a_default() -> None:
    rot = default_rotation()
    stale = replace(rot, age_hours=rot.sla_hours + 1.0)
    it = classify_write_intent("Page the oncall for the payments outage", oncall=stale)
    assert it.status == AMBIGUOUS and it.reason_code == "no_recipient"
    assert "stale" in it.reason and it.payload.get("rotation_doc") == rot.doc_id


def test_no_rotation_means_no_default() -> None:
    it = classify_write_intent("Page the oncall", oncall=None)
    assert it.status == AMBIGUOUS and it.reason_code == "no_recipient"
    # A named registered recipient still works without a rotation.
    assert classify_write_intent("Page cache-oncall", oncall=None).status == PROPOSE


def test_copilot_rotation_follows_its_clock() -> None:
    # wiki_oncall_now is 16h old at the eval clock (confluence SLA 168h); a
    # clock 8 days later makes it stale, so a generic page must ask.
    assert Copilot().ask("Page the oncall for the payments outage").decision is Decision.PROPOSE_WRITE
    later = Copilot(now="2026-09-21T00:00:00Z")
    res = later.ask("Page the oncall for the payments outage")
    assert res.decision is Decision.REFUSE_AMBIGUOUS_WRITE
    assert res.explanation["write"]["reason_code"] == "no_recipient"
