"""dev5 CI report step: frozen split, held-out audit, tune-only scoring, known open bug."""

import json
import subprocess
import sys
from pathlib import Path

from ops_copilot.synonym_dev5 import half

ROOT = Path(__file__).resolve().parents[1]


def test_ci_script_freezes_the_same_split_sizes_and_never_scores_confirm():
    src = (ROOT / "scripts" / "run_dev5_eval.py").read_text(encoding="utf-8")
    assert 'FROZEN = {"tune": 24, "confirm": 20}' in src
    assert 'KNOWN_OPEN = ("d5-38",)' in src
    assert len(half("tune")) == 24 and len(half("confirm")) == 20


def test_ci_step_is_in_the_workflow():
    wf = (ROOT / ".github" / "workflows" / "eval.yml").read_text(encoding="utf-8")
    assert "python scripts/run_dev5_eval.py" in wf and "artifacts/synonym_dev5_eval.json" in wf


def test_committed_report_matches_a_fresh_run():
    committed = json.loads((ROOT / "artifacts" / "synonym_dev5_eval.json").read_text())
    subprocess.run([sys.executable, str(ROOT / "scripts" / "run_dev5_eval.py")], check=True,
                   capture_output=True, text=True)
    fresh = json.loads((ROOT / "artifacts" / "synonym_dev5_eval.json").read_text())
    assert fresh == committed
    assert fresh["vocabulary_problems"] == {} and fresh["heldout_words_in_file"] == []
    assert fresh["confirm_scored"] is False and fresh["unexpected_open"] == []
    t = fresh["tune_default"]
    assert (t["correct"], t["n"], t["must_refuse_opened"]) == (10, 24, ["d5-38"])
