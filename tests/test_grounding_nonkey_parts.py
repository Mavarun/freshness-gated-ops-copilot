"""Evidence-side compound parts for the non-key rule (``grounding_nonkey_parts``, off)."""

import dataclasses

import pytest

from ops_copilot.config import CopilotConfig
from ops_copilot.grounding import NONKEY_PARTS, Grounder, evidence_part_forms
from ops_copilot.pipeline import Copilot


def _bot(**kw):
    return Copilot(config=dataclasses.replace(CopilotConfig(), **kw))


@pytest.fixture(scope="module")
def bots():
    return {
        "all": _bot(grounding_nonkey_rule="all"),
        "hyphen": _bot(grounding_nonkey_rule="all", grounding_nonkey_parts="hyphen"),
        "joined": _bot(grounding_nonkey_rule="all", grounding_nonkey_parts="joined"),
        "off_hyphen": _bot(grounding_nonkey_parts="hyphen"),
    }


def test_parts_are_off_by_default():
    assert CopilotConfig().grounding_nonkey_parts == "off"
    assert Copilot().grounder.nonkey_parts == "off"


def test_unknown_mode_is_rejected():
    with pytest.raises(ValueError):
        Grounder(["a b c"], nonkey_parts="dots")


def test_part_forms_split_hyphens_and_drop_identifier_fragments():
    f = evidence_part_forms("Primary is Asha (pager checkout-primary) in us-east-1 on p99-api", "hyphen")
    assert {"checkout", "primary", "api"} <= f
    assert "us" not in f and "east" in f and "p99" not in f
    assert "checkouts" in f  # plural variant, same as the lexical matcher


def test_hyphen_mode_leaves_underscores_alone_and_joined_splits_them():
    text = "Feature flag checkout_retry is enabled"
    assert "retry" not in evidence_part_forms(text, "hyphen")
    assert {"checkout", "retry"} <= evidence_part_forms(text, "joined")
    assert evidence_part_forms(text, "off") == frozenset()


def test_off_mode_matches_the_old_rule(bots):
    # dev8 (spent, now calibration) row d8-06: 'checkout' is only in the pager name
    q = "Who is the primary on-call right now for checkout?"
    res = bots["all"].ask(q)
    assert res.decision.value == "REFUSE_UNGROUNDED"
    assert "checkout" in res.grounding.nonkey_unsupported


@pytest.mark.parametrize("mode", ["hyphen", "joined"])
def test_parts_credit_a_word_inside_a_cited_compound(bots, mode):
    res = bots[mode].ask("Who is the primary on-call right now for checkout?")
    assert res.decision.value == "ANSWER"
    assert res.grounding.nonkey_unsupported == []


@pytest.mark.parametrize("mode", ["hyphen", "joined"])
def test_parts_do_not_rescue_a_random_low_half_swap(bots, mode):
    # the Nov 9 swap: 'token' is in no evidence token; its synonym alt 'secret' is a
    # part of 'platform-secrets', which must not count
    res = bots[mode].ask("What is the Vault AppRole token schedule?")
    assert res.decision.value == "REFUSE_UNGROUNDED"
    assert res.grounding.nonkey_unsupported == ["token"]


def test_parts_need_the_rule(bots):
    # with grounding_nonkey_rule off the parts knob changes nothing
    q = "What is the Vault AppRole token schedule?"
    assert bots["off_hyphen"].ask(q).decision.value == Copilot().ask(q).decision.value == "ANSWER"


def test_parts_never_touch_the_key_gate():
    g = Grounder(["pager checkout-primary for asha", "other text here"], nonkey_rule="all", nonkey_parts="hyphen")
    # 'checkout' is a key term here; parts only relax the non-key check
    assert not g.keys_supported("checkout pager", "pager checkout-primary")


def test_modes_tuple():
    assert NONKEY_PARTS == ("off", "hyphen", "joined")

