"""The passage classifier as a grounding backoff: scope, strictness, traces."""

from __future__ import annotations

from dataclasses import replace

import pytest

from ops_copilot.config import CopilotConfig
from ops_copilot.corpus import Corpus
from ops_copilot.grounding import Grounder
from ops_copilot.passage_support import PassageSupportModel


@pytest.fixture(scope="module")
def chunks():
    return Corpus().chunks


def _grounder(chunks, **kw) -> Grounder:
    texts = [f"{c.title} {c.text}" for c in chunks]
    return Grounder(texts, passage_support=PassageSupportModel.load(), **kw)


def _latency_chunk(chunks):
    return [c for c in chunks if c.doc_id == "pd_inc_4821"][:1]


def test_off_by_default() -> None:
    from ops_copilot.pipeline import Copilot

    assert CopilotConfig().use_passage_support_model is False
    bot = Copilot()
    assert bot.passage_support is None
    g = bot.ask("What is the current checkout p99 latency?").as_dict()["grounding"]
    assert g["passage_rescued"] == [] and g["passage_probability"] is None


def test_rescues_one_missing_plain_word_above_threshold(chunks) -> None:
    gr = _grounder(chunks, passage_min_prob=0.0)
    res = gr.check("What is the checkout p99 delay?", _latency_chunk(chunks), "Checkout p99 latency climbed to 2410 milliseconds.")
    assert res.passage_rescued == ["delay<-latency"]
    assert 0.0 < res.passage_probability < 1.0


def test_threshold_blocks_but_probability_is_reported(chunks) -> None:
    gr = _grounder(chunks, passage_min_prob=0.99)
    res = gr.check("What is the checkout p99 delay?", _latency_chunk(chunks), "x")
    assert res.passage_rescued == [] and res.passage_probability is not None


def test_strict_mode_needs_a_wh_question(chunks) -> None:
    gr = _grounder(chunks, passage_min_prob=0.0)
    assert gr.check("checkout p99 delay", _latency_chunk(chunks), "x").passage_rescued == []
    loose = _grounder(chunks, passage_min_prob=0.0, passage_strict=False)
    assert loose.check("checkout p99 delay", _latency_chunk(chunks), "x").passage_rescued == ["delay<-latency"]


def test_identifiers_are_never_vouched_for(chunks) -> None:
    gr = _grounder(chunks, passage_min_prob=0.0)
    # p98 is an identifier the evidence lacks: strict mode refuses to rescue anything
    assert gr.check("What is the checkout p98 delay?", _latency_chunk(chunks), "x").passage_rescued == []
    loose = _grounder(chunks, passage_min_prob=0.0, passage_strict=False, passage_max_terms=3)
    assert all(not r.startswith("p98") for r in loose.check("What is the checkout p98 delay?", _latency_chunk(chunks), "x").passage_rescued)


def test_max_terms_caps_the_rescue(chunks) -> None:
    gr = _grounder(chunks, passage_min_prob=0.0, passage_max_terms=1)
    assert gr.check("What is the checkout p99 delay spike?", _latency_chunk(chunks), "x").passage_rescued == []


def test_known_word_scope(chunks) -> None:
    from ops_copilot.grounding import QueryTerm

    on = _grounder(chunks, passage_known=True)
    off = _grounder(chunks, passage_known=False)
    known = QueryTerm("incident", "known", 1.0, frozenset({"incident"}))
    unknown = QueryTerm("delay", "unknown", 1.0, frozenset({"delay"}))
    ident = QueryTerm("p99", "identifier", 1.0, frozenset({"p99"}))
    assert on.passage_eligible(known) and not off.passage_eligible(known)
    assert on.passage_eligible(unknown) and off.passage_eligible(unknown)
    assert not on.passage_eligible(ident)


def test_pipeline_wires_the_config() -> None:
    from ops_copilot.pipeline import Copilot

    cfg = replace(CopilotConfig(), use_passage_support_model=True, passage_support_min_prob=0.42, passage_support_max_terms=2)
    bot = Copilot(config=cfg)
    assert bot.passage_support is not None
    assert bot.grounder.passage_min_prob == 0.42 and bot.grounder.passage_max_terms == 2
    assert bot.grounder.passage_strict is True
