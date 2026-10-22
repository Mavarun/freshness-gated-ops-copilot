"""dev4 CI report step: frozen split, held-out audit, must-refuse rows, and a reproducible report."""

import json
import subprocess
import sys
from pathlib import Path

from ops_copilot.synonym_dev4 import half

ROOT = Path(__file__).resolve().parents[1]


def test_ci_script_freezes_the_same_split_sizes():
    src = (ROOT / "scripts" / "run_dev4_eval.py").read_text(encoding="utf-8")
    assert 'FROZEN = {"tune": 23, "confirm": 21}' in src
    assert len(half("tune")) == 23 and len(half("confirm")) == 21


def test_ci_step_is_in_the_workflow():
    wf = (ROOT / ".github" / "workflows" / "eval.yml").read_text(encoding="utf-8")
    assert "python scripts/run_dev4_eval.py" in wf and "artifacts/synonym_dev4_eval.json" in wf


def test_committed_report_matches_a_fresh_run():
    committed = json.loads((ROOT / "artifacts" / "synonym_dev4_eval.json").read_text())
    subprocess.run([sys.executable, str(ROOT / "scripts" / "run_dev4_eval.py")], check=True,
                   capture_output=True, text=True)
    fresh = json.loads((ROOT / "artifacts" / "synonym_dev4_eval.json").read_text())
    assert fresh == committed
    assert fresh["vocabulary_problems"] == {} and fresh["heldout_words_in_file"] == []
    default = fresh["halves"]["confirm"]["default (shipped)"]
    assert (default["correct"], default["n_fail_open"], default["must_refuse_opened"]) == (7, 0, [])
    arm = next(v for k, v in fresh["halves"]["confirm"].items() if k.startswith("Datamuse"))
    assert (arm["correct"], arm["must_refuse_opened"]) == (10, ["d4-37"])
