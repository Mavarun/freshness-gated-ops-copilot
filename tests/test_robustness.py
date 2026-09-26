from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from ops_copilot.eval import load_golden
from ops_copilot.paraphrase_set import dump_jsonl, load_paraphrase_set
from ops_copilot.perturb import PERTURBATION_TYPES
from ops_copilot.robustness import classify_flip, run_robustness

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
