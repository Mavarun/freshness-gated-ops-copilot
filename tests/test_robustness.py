from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from ops_copilot.eval import load_golden
from ops_copilot.paraphrase_set import dump_jsonl, load_paraphrase_set
from ops_copilot.perturb import PERTURBATION_TYPES
from ops_copilot.robustness import (
    ABLATIONS,
    EMBED_ABLATIONS,
    PR10_BEFORE,
    PR11_BEFORE,
    PHRASAL_ABLATIONS,
    PR12_BEFORE,
    PR13_BEFORE,
    WRITE_ABLATIONS,
    classify_flip,
    load_before,
    run_robustness,
)

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def report():
    return run_robustness()


def test_label_drift_is_rejected(tmp_path: Path) -> None:
    rows = load_paraphrase_set()[:3]
    flipped = "REFUSE_STALE" if rows[0]["expect_decision"] == "ANSWER" else "ANSWER"
    rows[0] = dict(rows[0], expect_decision=flipped)
    bad = dump_jsonl(rows, tmp_path / "bad.jsonl")
    with pytest.raises(ValueError, match="label drifted"):
        run_robustness(paraphrase_path=bad)


def test_report_structure(report) -> None:
    d = report.as_dict()
    assert d["n_clean"] == len(load_golden())
    assert d["clean_accuracy"] == pytest.approx(1.0)
    assert d["n_perturbed"] == len(load_paraphrase_set())
    assert set(d["per_perturbation"]) == set(PERTURBATION_TYPES)
    assert sum(b["n"] for b in d["per_perturbation"].values()) == d["n_perturbed"]
    assert sum(b["n"] for b in d["per_gate"].values()) == d["n_perturbed"]
    assert d["n_flips"] == len(d["flips"]) == sum(d["flip_kinds"].values())
    # The finding, not a threshold: perturbation must not *raise* accuracy here.
    assert 0.0 <= d["perturbed_accuracy"] <= d["clean_accuracy"]


def test_budget_gate_is_perturbation_invariant(report) -> None:
    assert report.per_gate["REFUSE_BUDGET"]["perturbed_accuracy"] == pytest.approx(1.0)


def test_no_raw_pii_in_perturbed_outputs(report) -> None:
    assert not any(c.raw_pii_in_output for c in report.cases)


def test_classify_flip() -> None:
    assert classify_flip("ANSWER", "ANSWER") == "ok"
    assert classify_flip("REFUSE_PII", "ANSWER") == "fail_open"
    assert classify_flip("ANSWER", "REFUSE_UNGROUNDED") == "over_refusal"
    assert classify_flip("REFUSE_STALE", "REFUSE_UNGROUNDED") == "wrong_refusal_reason"
    assert classify_flip("PROPOSE_WRITE", "REFUSE_UNGROUNDED") == "missed_write"
    assert classify_flip("REFUSE_UNGROUNDED", "PROPOSE_WRITE") == "spurious_write"


def test_run_script_writes_artifacts(tmp_path: Path) -> None:
    proc = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "run_robustness.py"), "--out-dir", str(tmp_path)],
        capture_output=True,
        text=True,
        check=True,
    )
    assert "perturbed_accuracy=" in proc.stdout
    md = (tmp_path / "robustness_report.md").read_text(encoding="utf-8")
    assert "## Per gate (expected decision)" in md
    metrics = json.loads((tmp_path / "robustness_metrics.json").read_text(encoding="utf-8"))
    assert {"clean_accuracy", "perturbed_accuracy", "per_gate", "flips"} <= set(metrics)
    # Committed artifact (quoted in README) must match a fresh deterministic run.
    committed = json.loads((ROOT / "artifacts" / "robustness_metrics.json").read_text("utf-8"))
    assert metrics == committed


def test_synonym_rows_are_split_dev_and_heldout(report) -> None:
    sp = report.per_synonym_split
    assert set(sp) == {"dev", "heldout"}
    assert sp["dev"]["n"] + sp["heldout"]["n"] == report.per_perturbation["synonym"]["n"]
    for c in report.cases:
        if c.perturbation == "synonym":
            assert c.synonym_split in {"dev", "heldout"}, c.id
        else:
            assert c.synonym_split == "", c.id
    assert report.as_dict()["per_synonym_split"] == sp


def test_before_is_the_frozen_pr13_run_rescored_with_the_split() -> None:
    before = load_before()
    assert before is not None
    assert "135c57f" in before["source"] and before["label"] == "PR #13"
    assert before["perturbed_accuracy"] == pytest.approx(0.8719, abs=1e-4)
    assert len(before["decisions"]) == 203
    held = before["per_synonym_split"]["heldout"]
    assert held["n"] == 35 and held["perturbed_accuracy"] == pytest.approx(15 / 35)
    emb = before["embedding_on"]
    assert emb["label"] == "PR #13 (embedding on)"
    assert emb["perturbed_accuracy"] == pytest.approx(0.8966, abs=1e-4)
    assert emb["per_synonym_split"]["heldout"]["perturbed_accuracy"] == pytest.approx(18 / 35)


def test_phrasal_slice_changes_no_robustness_row(report) -> None:
    # The phrasal verbs, registry targets and page recipients move no row of
    # the 203: the perturbed set's write rows use none of the new phrasings,
    # and its held-out phrasal words (set/turn/down/flush/purge) sit in
    # question rows. Pinned so a regression shows up as a changed row.
    before = load_before(PR13_BEFORE)
    actual = {c.id: c.perturbed_decision for c in report.cases}
    assert {rid: d for rid, d in actual.items() if d != before["decisions"][rid]} == {}


def test_pr12_run_stays_loadable_for_history() -> None:
    before = load_before(PR12_BEFORE)
    assert before is not None
    assert "fcc8157" in before["source"] and before["label"] == "PR #12"
    assert before["perturbed_accuracy"] == pytest.approx(0.8621, abs=1e-4)
    assert len(before["decisions"]) == 203
    held = before["per_synonym_split"]["heldout"]
    assert held["n"] == 35 and held["perturbed_accuracy"] == pytest.approx(0.4)
    assert held["by_gate"]["PROPOSE_WRITE"] == {"n": 3, "correct": 0}
    emb = before["embedding_on"]
    assert emb["label"] == "PR #12 (embedding on)"
    assert emb["perturbed_accuracy"] == pytest.approx(0.8867, abs=1e-4)
    assert emb["per_synonym_split"]["dev"]["perturbed_accuracy"] == pytest.approx(11 / 15)
    assert emb["per_synonym_split"]["heldout"]["perturbed_accuracy"] == pytest.approx(17 / 35)
    by_gate = emb["per_synonym_split"]["heldout"]["by_gate"]
    assert by_gate["ANSWER"]["correct"] + by_gate["PROPOSE_WRITE"]["correct"] == 1


def test_pr11_run_stays_loadable_for_history() -> None:
    pr11 = load_before(PR11_BEFORE)
    assert pr11 is not None and pr11["label"] == "PR #11"
    assert "31fceb0" in pr11["source"]
    assert pr11["per_synonym_split"]["heldout"]["perturbed_accuracy"] == pytest.approx(0.4)


def test_pr10_run_stays_loadable_for_history() -> None:
    pr10 = load_before(PR10_BEFORE)
    assert pr10 is not None and pr10["label"] == "PR #10"
    assert "00cacb5" in pr10["source"]
    assert pr10["perturbed_accuracy"] == pytest.approx(0.8916, abs=1e-4)


# The structured write parser changes exactly these rows of the PR #12 run:
# the dev 'update ... setting' and held-out 'page the on-duty engineer' rows
# are now proposed; 'bounce' / 'reboot' (held-out verbs, not in any lexicon)
# become a clarifying refusal instead of REFUSE_UNGROUNDED.
WRITE_PARSER_CHANGES = {
    "g41-synonym": "REFUSE_AMBIGUOUS_WRITE",
    "g42-synonym": "PROPOSE_WRITE",
    "g43-synonym": "PROPOSE_WRITE",
    "g44-synonym": "REFUSE_AMBIGUOUS_WRITE",
}


def test_default_config_matches_pr12_except_the_parsed_writes(report) -> None:
    before = load_before(PR12_BEFORE)
    assert before is not None and "fcc8157" in before["source"]
    actual = {c.id: c.perturbed_decision for c in report.cases}
    changed = {rid: d for rid, d in actual.items() if d != before["decisions"][rid]}
    assert changed == WRITE_PARSER_CHANGES


def test_embedding_ablations_only_toggle_embedding_knobs() -> None:
    assert set(EMBED_ABLATIONS) == {
        "embedding retriever only",
        "semantic grounding only",
        "both (embedding on)",
        "both, strict off (unsafe)",
    }
    allowed = {
        "embedding_backend",
        "embed_dense_retriever",
        "embed_semantic_grounding",
        "semantic_grounding_strict",
    }
    for knobs in EMBED_ABLATIONS.values():
        assert knobs["embedding_backend"] == "frozen"
        assert set(knobs) <= allowed


def test_ablation_grid_toggles_only_the_synonym_sources() -> None:
    assert set(ABLATIONS) == {
        "no map, no embedding",
        "map only (leakage-free)",
        "embedding only",
        "map + embedding",
    }
    for knobs in ABLATIONS.values():
        assert set(knobs) == {"use_synonyms", "use_semantic_backoff"}


def test_write_ablations_only_toggle_write_knobs() -> None:
    from ops_copilot.write_eval import WRITE_EVAL_CONFIGS

    assert WRITE_ABLATIONS == WRITE_EVAL_CONFIGS
    allowed = {"write_mood_detection", "write_prototype_backoff", "embedding_backend"}
    for knobs in WRITE_ABLATIONS.values():
        assert set(knobs) <= allowed


def test_committed_write_ablation_safety() -> None:
    metrics = json.loads((ROOT / "artifacts" / "robustness_metrics.json").read_text("utf-8"))
    rows = metrics["write_ablations"]
    assert list(rows) == list(WRITE_ABLATIONS) + list(PHRASAL_ABLATIONS)
    for label, row in rows.items():
        if label.startswith("lexicon parser only"):
            # Why mood detection exists: 'How do I restart ...' becomes a write.
            assert row["n_spurious_write"] > 0
            assert row["clean_safety"]["n_spurious_write"] > 0
            continue
        assert row["clean_accuracy"] == 1.0, label
        assert row["n_fail_open"] == row["n_spurious_write"] == row["n_raw_pii_outputs"] == 0
        assert row["clean_safety"] == {"n_fail_open": 0, "n_spurious_write": 0, "n_raw_pii_outputs": 0}
    backoff = rows["+ mood + prototype backoff (embedding on)"]
    assert backoff["heldout_write_correct"] == "2/3"  # page (lexicon) + reboot (backoff)
