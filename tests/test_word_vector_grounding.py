"""Word-vector backoff wiring: grounding terms, known-word scope, rewrite."""

from __future__ import annotations

from dataclasses import replace

import pytest

from ops_copilot import Copilot, CopilotConfig
from ops_copilot.grounding import Grounder
from ops_copilot.word_vectors import WordVectorBackoff

TEXTS = [
    "Requests route through the edge proxy before checkout.",
    "The failover path is documented. Start the drill on Monday.",
]


def _grounder(*, known: bool = False, th: float = 0.80) -> Grounder:
    wv = WordVectorBackoff(TEXTS, min_similarity=th, max_neighbours=1)
    return Grounder(TEXTS, wordvec=wv, wordvec_known=known)


def test_unknown_word_gets_its_counter_fitted_substitute() -> None:
    g = _grounder()
    term = next(t for t in g.terms("When do we begin the drill?") if t.token == "begin")
    assert term.kind == "wordvec"
    assert "start" in term.alts
    assert term.weight == g._weight("start")  # weighted like its substitute


def test_without_backoff_the_word_stays_unknown() -> None:
    g = Grounder(TEXTS)
    term = next(t for t in g.terms("When do we begin the drill?") if t.token == "begin")
    assert term.kind == "unknown" and term.alts == frozenset({"begin"})


def test_known_word_scope_is_opt_in() -> None:
    off = _grounder(known=False)
    on = _grounder(known=True)
    q = "Where is the failover route documented?"
    assert "path" not in next(t for t in off.terms(q) if t.token == "route").alts
    route = next(t for t in on.terms(q) if t.token == "route")
    assert route.kind == "known" and "path" in route.alts
    sup = on.support(q, TEXTS[1])
    assert sup.ok(route)


def test_identifiers_and_numbers_never_get_substitutes() -> None:
    q = "Is checkout-api p99 above 300 ms?"
    plain = {t.token: t for t in Grounder(TEXTS).terms(q)}
    on = {t.token: t for t in _grounder(known=True, th=0.5).terms(q)}
    for tok in ("checkout-api", "p99", "300"):
        assert on[tok].kind == plain[tok].kind == "identifier"
        assert on[tok].alts == plain[tok].alts


def test_threshold_is_respected() -> None:
    g = _grounder(th=0.99)  # begin~start is 0.94 in the source vectors
    term = next(t for t in g.terms("When do we begin the drill?") if t.token == "begin")
    assert term.kind == "unknown"


@pytest.fixture(scope="module")
def bot_on() -> Copilot:
    return Copilot(config=replace(CopilotConfig(), use_word_vector_backoff=True))


def test_retrieval_rewrite_uses_substitutes(bot_on: Copilot) -> None:
    rq = bot_on.retriever.rewrite_query("How do we begin a deploy?")
    assert "start" in rq.split() and "begin" not in rq.split()


def test_backoff_is_built_only_when_enabled(copilot: Copilot, bot_on: Copilot) -> None:
    assert copilot.wordvec is None or copilot.config.use_word_vector_backoff
    assert bot_on.wordvec is not None
    assert bot_on.grounder.wordvec is bot_on.wordvec
    assert bot_on.retriever.wordvec is bot_on.wordvec
