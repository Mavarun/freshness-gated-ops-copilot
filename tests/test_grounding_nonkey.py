import dataclasses

import pytest

from ops_copilot.config import CopilotConfig
from ops_copilot.grounding import NONKEY_RULES, Grounder, _quantile
from ops_copilot.pipeline import Copilot


def _bot(**kw):
    return Copilot(config=dataclasses.replace(CopilotConfig(), **kw))


@pytest.fixture(scope="module")
def bots():
    return {r: _bot(grounding_nonkey_rule=r) for r in NONKEY_RULES}


def test_rule_is_off_by_default():
    assert CopilotConfig().grounding_nonkey_rule == "off"
    assert Copilot().grounder.nonkey_rule == "off"


def test_unknown_rule_is_rejected():
    with pytest.raises(ValueError):
        Grounder(["a b c"], nonkey_rule="strict")


def test_quantile_is_lower_empirical_and_clamped():
    v = [1.0, 2.0, 3.0, 4.0]
    assert _quantile(v, 0.0) == 1.0
    assert _quantile(v, 0.5) == 3.0
    assert _quantile(v, 1.0) == 4.0
    assert _quantile(v, 7.0) == 4.0
    assert _quantile([], 0.5) == 0.0


def test_off_answers_a_low_half_random_swap(bots):
    # 'token' replaced 'rotation'; it sits in the low-IDF half and nothing supports it
    res = bots["off"].ask("What is the Vault AppRole token schedule?")
    assert res.decision.value == "ANSWER"
    assert res.grounding.nonkey_unsupported == []
    assert "nonkey_unsupported" not in res.grounding.as_dict()


@pytest.mark.parametrize("rule", ["all", "corpus"])
def test_all_and_corpus_refuse_the_swap_and_name_the_word(bots, rule):
    res = bots[rule].ask("What is the Vault AppRole token schedule?")
    assert res.decision.value == "REFUSE_UNGROUNDED"
    assert res.grounding.nonkey_unsupported == ["token"]
    assert res.grounding.as_dict()["nonkey_unsupported"] == ["token"]


@pytest.mark.parametrize("rule", NONKEY_RULES)
def test_every_rule_keeps_the_original_question(bots, rule):
    for q in ("What is the Vault AppRole rotation schedule?", "Who is the primary on-call right now?"):
        assert bots[rule].ask(q).decision.value == "ANSWER"


def test_corpus_rule_skips_outside_words():
    g = Copilot().grounder
    g.nonkey_rule = "corpus"
    terms = g.terms("What is the remaining error margin for checkout?")
    kinds = {t.token: t.kind for t in terms}
    assert kinds.get("margin") not in (None, "known", "typo", "identifier")
    # an unsupported outside word never enters the list under 'corpus'
    sup = g.support("What is the remaining error margin for checkout?", "remaining error checkout")
    assert "margin" not in g.nonkey_unsupported(sup)


def test_idf_rule_uses_the_corpus_quantile():
    lo = _bot(grounding_nonkey_rule="idf", grounding_nonkey_idf_quantile=0.0).grounder
    hi = _bot(grounding_nonkey_rule="idf", grounding_nonkey_idf_quantile=1.0).grounder
    assert lo.nonkey_min_idf == min(lo.idf.values())
    assert hi.nonkey_min_idf == max(hi.idf.values())
    # at quantile 0 every unsupported non-key term counts, like 'all'
    q = "What is the Vault AppRole token schedule?"
    assert _bot(grounding_nonkey_rule="idf", grounding_nonkey_idf_quantile=0.0).ask(q).decision.value == "REFUSE_UNGROUNDED"
