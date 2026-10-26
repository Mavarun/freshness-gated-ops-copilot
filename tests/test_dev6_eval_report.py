"""dev6 CI report step: frozen size, held-out audit, shipped default opens no must-refuse row."""

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_ci_step_is_in_the_workflow_and_uploads_its_report():
    wf = (ROOT / ".github" / "workflows" / "eval.yml").read_text(encoding="utf-8")
    assert "python scripts/run_dev6_eval.py" in wf and "artifacts/synonym_dev6_eval.json" in wf


def test_committed_report_matches_a_fresh_run_and_agrees_with_the_confirm_off_arm():
    committed = json.loads((ROOT / "artifacts" / "synonym_dev6_eval.json").read_text())
    subprocess.run([sys.executable, str(ROOT / "scripts" / "run_dev6_eval.py")], check=True,
                   capture_output=True, text=True)
    fresh = json.loads((ROOT / "artifacts" / "synonym_dev6_eval.json").read_text())
    assert fresh == committed
    assert fresh["vocabulary_problems"] == {} and fresh["heldout_words_in_file"] == []
    d = fresh["default"]
    assert (d["correct"], d["n"], d["answer_correct"], d["n_answer"]) == (21, 45, 3, 24)
    assert d["must_refuse_opened"] == [] and d["n_fail_open"] == 0
    off = json.loads((ROOT / "artifacts" / "datamuse_dev6_confirm.json").read_text())["confirm"]["off"]
    assert (off["correct"], off["answer_correct"]) == (d["correct"], d["answer_correct"])
