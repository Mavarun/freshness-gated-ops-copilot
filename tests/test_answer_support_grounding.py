"""Grounder wiring of the evidence-conditioned answer-support model."""

from __future__ import annotations

from ops_copilot.grounding import Grounder
from ops_copilot.qa_translation import Translation, fold_token

CORPUS = [
    "Checkout p99 latency dashboard: checkout p99 latency is 2410 ms.",
    "Kafka consumer lag runbook for payments-worker.",
    "Payments-api status page: payments-api status is degraded.",
]


class StubModel:
    """Answers ``q`` by evidence word ``a`` with a fixed lift."""

    def __init__(self, pairs: dict[tuple[str, str], float], min_score: float = 2.0):
        self.pairs = pairs
        self.min_score = min_score

    def supports(self, q, evidence_words):
        best = None
        for e in evidence_words:
            s = self.pairs.get((fold_token(q), fold_token(e)))
            if s is not None and (best is None or s > best.score):
                best = Translation(q, e, s)
        return best if best is not None and best.score >= self.min_score else None


def _g(model, **kw) -> Grounder:
    return Grounder(CORPUS, answer_support=model, **kw)


EVIDENCE = CORPUS[0]


Q_LAG = "What is the checkout p99 lag?"


def test_off_by_default_known_word_in_another_sense_is_missing():
    g = Grounder(CORPUS)
    assert "lag" in g.missing_terms(Q_LAG, EVIDENCE)


def test_known_scope_rescues_a_corpus_word_used_in_another_sense():
    m = StubModel({("lag", "latency"): 3.0})
    # "lag" is a corpus word (consumer lag): the default scope leaves it alone
    assert "lag" in _g(m).missing_terms(Q_LAG, EVIDENCE)
    g = _g(m, answer_known=True)
    sup = g.support(Q_LAG, EVIDENCE)
    assert [(t.query_word, t.evidence_word) for t in sup.translated] == [("lag", "latency")]
    assert g.missing_terms(Q_LAG, EVIDENCE) == []
    assert g.coverage(Q_LAG, EVIDENCE)[0] == 1.0


def test_unknown_word_is_rescued_without_known_scope():
    m = StubModel({("health", "status"): 3.0})
    g = _g(m)
    assert g.keys_supported("What is the health of the payments-api?", CORPUS[2])


def test_below_threshold_is_not_support():
    m = StubModel({("health", "status"): 1.5})
    assert not _g(m).keys_supported("What is the health of the payments-api?", CORPUS[2])


def test_strict_mode_needs_a_wh_question():
    m = StubModel({("health", "status"): 3.0})
    g = _g(m)
    assert not g.support("Show health payments-api", CORPUS[2]).translated
    loose = _g(m, answer_strict=False)
    assert loose.support("Show health payments-api", CORPUS[2]).translated


def test_strict_mode_is_all_or_nothing_over_missing_words():
    # "zebra" has no translation, so strict mode rescues nothing at all
    m = StubModel({("health", "status"): 3.0})
    g = _g(m, answer_max_terms=2)
    assert not g.support("What is the zebra health of payments-api?", CORPUS[2]).translated
    loose = _g(m, answer_strict=False, answer_max_terms=2)
    got = loose.support("What is the zebra health of payments-api?", CORPUS[2]).translated
    assert [t.query_word for t in got] == ["health"]


def test_max_terms_caps_rescues():
    m = StubModel({("health", "status"): 3.0, ("condition", "degraded"): 3.0})
    q = "What is the health condition of payments-api?"
    assert not _g(m, answer_max_terms=1).support(q, CORPUS[2]).translated
    assert len(_g(m, answer_max_terms=2).support(q, CORPUS[2]).translated) == 2


def test_identifiers_are_never_translated():
    m = StubModel({("payments-api2", "payments-api"): 9.0})
    g = _g(m, answer_strict=False)
    assert not g.support("What is payments-api2 status?", CORPUS[2]).translated


def test_answer_coverage_check_stays_lexical():
    m = StubModel({("health", "status"): 3.0})
    g = _g(m)
    sup = g.support("health", CORPUS[2], semantic=False)
    assert not sup.translated


def test_check_reports_translation_pairs():
    from datetime import datetime, timezone

    from ops_copilot.types import Chunk

    m = StubModel({("health", "status"): 3.0})
    g = _g(m)
    chunk = Chunk(
        chunk_id="d#0",
        doc_id="d",
        title="Payments-api status page",
        text=CORPUS[2],
        updated_at=datetime(2026, 9, 13, tzinfo=timezone.utc),
        source_system="statuspage",
        age_hours=1.0,
    )
    res = g.check("What is the health of the payments-api?", [chunk], "payments-api status is degraded.")
    assert res.translation_rescued == ["health<-status"]
    assert res.as_dict()["translation_rescued"] == ["health<-status"]


def test_pipeline_loads_the_model_only_when_switched_on():
    from ops_copilot import Copilot, CopilotConfig

    assert Copilot(config=CopilotConfig()).answer_support is None
    bot = Copilot(config=CopilotConfig(use_answer_support_model=True))
    assert bot.answer_support is not None
    assert bot.grounder.answer_support is bot.answer_support
    res = bot.ask("What is the current checkout p99 latency?")
    assert res.decision.value == "ANSWER"  # lexically grounded rows are untouched
