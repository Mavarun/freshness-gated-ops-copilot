from __future__ import annotations

import pytest

from ops_copilot.config import EVAL_CLOCK, parse_clock
from ops_copilot.corpus import Corpus, age_hours
from ops_copilot.freshness import age_passes, check_freshness
from ops_copilot.types import FreshnessStatus

from conftest import make_chunk


def test_age_hours_exact_day() -> None:
    older = parse_clock("2026-09-12T00:00:00Z")
    assert age_hours(older, EVAL_CLOCK) == pytest.approx(24.0)


def test_age_hours_fractional() -> None:
    older = parse_clock("2026-09-12T22:15:00Z")
    assert age_hours(older, EVAL_CLOCK) == pytest.approx(1.75)


def test_inclusive_sla_boundary_passes() -> None:
    assert age_passes(48.0, 48.0) is True
    assert age_passes(47.999, 48.0) is True


def test_just_over_sla_fails() -> None:
    assert age_passes(48.0001, 48.0) is False
    assert age_passes(72.0, 48.0) is False


def test_zero_age_always_passes() -> None:
    assert age_passes(0.0, 48.0) is True
    assert age_passes(0.0, 0.0) is True


def test_negative_sla_rejected() -> None:
    with pytest.raises(ValueError):
        age_passes(1.0, -1.0)


def test_check_freshness_pass_fail_payload() -> None:
    fresh = check_freshness(make_chunk("f", hours_old=3.0), max_age_hours=48.0)
    stale = check_freshness(make_chunk("s", hours_old=100.0), max_age_hours=48.0)
    assert fresh.status is FreshnessStatus.PASS
    assert fresh.age_hours == pytest.approx(3.0)
    assert stale.status is FreshnessStatus.FAIL
    assert stale.doc_id == "s"


def test_corpus_ages_use_frozen_clock() -> None:
    corpus = Corpus(now=EVAL_CLOCK)
    ages = {d.doc_id: age_hours(d.updated_at, EVAL_CLOCK) for d in corpus.docs}
    assert ages["pd_inc_4821"] < 48.0
    assert ages["rb_redis_maxmemory"] > 48.0
    assert min(c.age_hours for c in corpus.chunks) >= 0.0
