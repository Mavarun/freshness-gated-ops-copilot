import dataclasses
import json
from pathlib import Path

from ops_copilot.citation_keep import (
    DEV9_MAX_LOST,
    citation_counts,
    dev9_ships_citation_rule,
    evidence_ok,
    load_dev9_docs,
)
from ops_copilot.config import CopilotConfig
from ops_copilot.pipeline import Copilot

ROOT = Path(__file__).resolve().parents[1]
GOLDEN = [json.loads(x) for x in (ROOT / "data/golden/questions.jsonl").read_text().splitlines() if x.strip()]


def _rows(name):
    return [json.loads(x) for x in (ROOT / "data/eval" / name).read_text().splitlines() if x.strip()]


def test_dev9_labels_cover_exactly_the_wordy_rows_with_real_doc_ids():
    labels = load_dev9_docs()
    wordy = [r["id"] for r in _rows("nonkey_dev9.jsonl") if r["kind"] == "wordy"]
    assert sorted(labels) == sorted(wordy) and len(labels) == 32
    ids = {json.loads(x)["doc_id"] for x in (ROOT / "data/corpus/ops_docs.jsonl").read_text().splitlines() if x.strip()}
    assert all(v and v <= ids for v in labels.values())


def test_d6_06_is_a_wrong_evidence_answer_under_the_shipped_default():
    bot = Copilot()
    row = next(r for r in _rows("synonym_dev6.jsonl") if r["id"] == "d6-06")
    assert evidence_ok(bot, row, GOLDEN, {}) is False


def test_a_refused_wrong_evidence_row_counts_as_fixed_not_lost():
    ref = Copilot()
    arm = Copilot(config=dataclasses.replace(CopilotConfig(), grounding_nonkey_rule="all"))
    row = next(r for r in _rows("synonym_dev6.jsonl") if r["id"] == "d6-06")
    c = citation_counts(arm, ref, [row], GOLDEN)
    assert c["decision_lost"] == ["d6-06"] and c["fixed"] == ["d6-06"]
    assert c["lost"] == [] and c["budget_lost"] == 0


def test_identical_bots_lose_nothing():
    ref = Copilot()
    rows = [dict(r, id=f"g{i:02d}", source_index=i) for i, r in enumerate(GOLDEN[:8])]
    c = citation_counts(ref, ref, rows, GOLDEN)
    assert c["budget_lost"] == 0 and c["new_wrong"] == [] and c["fixed"] == []


def test_dev9_rule():
    base = {"lost": [], "fixed": ["x"], "new_wrong": [], "unknown_lost": [], "budget_lost": 0}
    assert dev9_ships_citation_rule(base)
    assert not dev9_ships_citation_rule(dict(base, budget_lost=DEV9_MAX_LOST + 1))
    assert not dev9_ships_citation_rule(dict(base, new_wrong=["y"]))
