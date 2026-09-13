from __future__ import annotations

from ops_copilot import Copilot


def test_retrieves_fresh_checkout_latency(copilot: Copilot) -> None:
    hits = copilot.retriever.search("current checkout p99 latency")
    ids = {h.doc_id for h in hits}
    assert "graf_checkout_sli" in ids or "pd_inc_4821" in ids
    assert hits[0].score >= hits[-1].score


def test_retrieves_stale_redis_policy(copilot: Copilot) -> None:
    hits = copilot.retriever.search("Redis maxmemory-policy")
    assert any(h.doc_id == "rb_redis_maxmemory" for h in hits)


def test_no_hits_for_absent_product(copilot: Copilot) -> None:
    hits = copilot.retriever.search("SAP payroll connector reset")
    assert hits == []


def test_hit_metadata_includes_source_and_age(copilot: Copilot) -> None:
    hits = copilot.retriever.search("checkout-api replicas")
    assert hits
    hit = hits[0]
    assert hit.source_system
    assert hit.updated_at.tzinfo is not None
    assert hit.age_hours >= 0
    assert hit.chunk_id.startswith(hit.doc_id)
