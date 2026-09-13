"""Per-source SLA loader + freshness matrix tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from ops_copilot import Copilot, CopilotConfig
from ops_copilot.freshness import annotate, check_freshness, fresh_only
from ops_copilot.source_slas import load_source_slas, resolve_max_age
from ops_copilot.types import Decision, FreshnessStatus

from conftest import make_chunk

ROOT = Path(__file__).resolve().parents[1]
SLA_PATH = ROOT / "config" / "source_slas.yaml"


def test_load_source_slas_defaults() -> None:
    table = load_source_slas(SLA_PATH)
    assert table.global_default_hours == 48.0
    assert table.max_age_hours("grafana") == 1.0
    assert table.max_age_hours("confluence") == 168.0
    assert table.max_age_hours("datadog") == 8.0
    # Unknown source falls back to global.
    assert table.max_age_hours("mystery-bus") == 48.0
    assert table.max_age_hours("Grafana") == 1.0  # case-insensitive


def test_resolve_max_age_respects_use_flag() -> None:
    table = load_source_slas(SLA_PATH)
    assert resolve_max_age("grafana", table=table, use_source_slas=True) == 1.0
    assert (
        resolve_max_age(
            "grafana",
            table=table,
            global_default_hours=48.0,
            use_source_slas=False,
        )
        == 48.0
    )


def test_per_source_matrix_pass_fail() -> None:
    """Same age, different source → different freshness outcome."""
    table = load_source_slas(SLA_PATH)
    age = 2.5  # hours

    graf = make_chunk("g", hours_old=age, source_system="grafana", text="qps is 920")
    wiki = make_chunk(
        "w",
        hours_old=age,
        source_system="confluence",
        text="maintenance change window is Saturday",
    )

    graf_fr = check_freshness(graf, sla_lookup=table.max_age_hours)
    wiki_fr = check_freshness(wiki, sla_lookup=table.max_age_hours)
    assert graf_fr.status is FreshnessStatus.FAIL  # 2.5 > 1h
    assert graf_fr.max_age_hours == 1.0
    assert wiki_fr.status is FreshnessStatus.PASS  # 2.5 < 168h
    assert wiki_fr.max_age_hours == 168.0


def test_annotate_applies_distinct_slas() -> None:
    table = load_source_slas(SLA_PATH)
    chunks = [
        make_chunk("g", hours_old=2.5, source_system="grafana"),
        make_chunk("c", hours_old=62.0, source_system="confluence"),
        make_chunk("r", hours_old=62.0, source_system="runbook"),
    ]
    results = annotate(chunks, sla_lookup=table.max_age_hours)
    by_id = {r.doc_id: r for r in results}
    assert by_id["g"].status is FreshnessStatus.FAIL
    assert by_id["c"].status is FreshnessStatus.PASS  # 62 <= 168
    assert by_id["r"].status is FreshnessStatus.FAIL  # 62 > 48


def test_fresh_only_filters_by_source_sla() -> None:
    table = load_source_slas(SLA_PATH)
    chunks = [
        make_chunk("g", hours_old=2.5, source_system="grafana"),
        make_chunk("c", hours_old=62.0, source_system="confluence"),
    ]
    kept = fresh_only(chunks, sla_lookup=table.max_age_hours)
    assert [c.doc_id for c in kept] == ["c"]


def test_global_only_vs_per_source_flip_wiki() -> None:
    """Confluence policy at ~62h: global refuses, per-source answers."""
    query = "What is the production maintenance change window?"
    global_bot = Copilot(config=CopilotConfig(use_source_slas=False, max_age_hours=48.0))
    per_bot = Copilot(config=CopilotConfig(use_source_slas=True, max_age_hours=48.0))
    g = global_bot.ask(query)
    p = per_bot.ask(query)
    assert g.decision is Decision.REFUSE_STALE, (g.decision, g.reason)
    assert p.decision is Decision.ANSWER, (p.decision, p.reason)
    assert "wiki_maint_window" in p.cited_ids


def test_global_only_vs_per_source_flip_grafana() -> None:
    """Grafana live scrape at ~2.5h: global answers, per-source refuses."""
    query = "What is the live payments-api request rate?"
    global_bot = Copilot(config=CopilotConfig(use_source_slas=False, max_age_hours=48.0))
    per_bot = Copilot(config=CopilotConfig(use_source_slas=True, max_age_hours=48.0))
    g = global_bot.ask(query)
    p = per_bot.ask(query)
    assert g.decision is Decision.ANSWER, (g.decision, g.reason)
    assert p.decision is Decision.REFUSE_STALE, (p.decision, p.reason)


def test_unknown_source_falls_back_to_global() -> None:
    table = load_source_slas(SLA_PATH)
    chunk = make_chunk("x", hours_old=30.0, source_system="totally-unknown")
    fr = check_freshness(chunk, sla_lookup=table.max_age_hours)
    assert fr.max_age_hours == 48.0
    assert fr.status is FreshnessStatus.PASS


def test_negative_sla_in_yaml_rejected(tmp_path: Path) -> None:
    bad = tmp_path / "bad.yaml"
    bad.write_text("global_default_hours: 48\nsources:\n  grafana: -1\n", encoding="utf-8")
    with pytest.raises(ValueError):
        load_source_slas(bad)


def test_missing_sla_file_raises() -> None:
    with pytest.raises(FileNotFoundError):
        load_source_slas("/tmp/does-not-exist-source-slas.yaml")
