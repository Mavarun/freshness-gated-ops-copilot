"""Guards on the fresh dev8 set (written 2026-11-09 before any arm was scored on it)."""

import json
from pathlib import Path

from ops_copilot.resource_audit import audit

ROOT = Path(__file__).resolve().parents[1]
REL = "data/eval/nonkey_dev8.jsonl"


def _rows(rel):
    return [json.loads(x) for x in (ROOT / rel).read_text(encoding="utf-8").splitlines() if x.strip()]


def test_frozen_size_and_ids():
    rows = _rows(REL)
    assert len(rows) == 48
    assert sum(r["expect_decision"] == "ANSWER" for r in rows) == 32
    assert sum(r["kind"] == "topic_trap" for r in rows) == 16
    assert len({r["id"] for r in rows}) == 48


def test_no_heldout_word_in_file():
    assert audit((REL,))[REL] == []


def test_no_query_repeats_an_older_eval_row():
    older = set()
    for p in sorted((ROOT / "data/eval").glob("*.jsonl")) + sorted((ROOT / "data/golden").glob("*.jsonl")):
        if p.name == "nonkey_dev8.jsonl":
            continue
        for r in _rows(p.relative_to(ROOT)):
            if "query" in r:
                older.add(r["query"].strip().lower())
    assert not [r["id"] for r in _rows(REL) if r["query"].strip().lower() in older]
