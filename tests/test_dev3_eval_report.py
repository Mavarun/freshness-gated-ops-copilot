"""dev3 CI report step: frozen sizes match the split, and the committed report matches a fresh run."""

import json
import subprocess
import sys
from pathlib import Path

from ops_copilot.synonym_dev3 import half

ROOT = Path(__file__).resolve().parents[1]


def test_ci_script_freezes_the_same_split_sizes():
    src = (ROOT / "scripts" / "run_dev3_eval.py").read_text(encoding="utf-8")
    assert 'FROZEN = {"calib": 25, "confirm": 20}' in src
    assert len(half("calib")) == 25 and len(half("confirm")) == 20


def test_ci_step_is_in_the_workflow():
    wf = (ROOT / ".github" / "workflows" / "eval.yml").read_text(encoding="utf-8")
    assert "python scripts/run_dev3_eval.py" in wf and "artifacts/synonym_dev3_eval.json" in wf


def test_committed_report_matches_a_fresh_run(tmp_path):
    committed = json.loads((ROOT / "artifacts" / "synonym_dev3_eval.json").read_text())
    subprocess.run([sys.executable, str(ROOT / "scripts" / "run_dev3_eval.py")], check=True,
                   capture_output=True, text=True)
    fresh = json.loads((ROOT / "artifacts" / "synonym_dev3_eval.json").read_text())
    assert fresh == committed
    default = fresh["halves"]["confirm"]["default (shipped)"]
    # 11 until 2026-10-25; the null-control test turns d3-27 (execute <- procedure)
    # from REFUSE_STALE into REFUSE_UNGROUNDED, a row already counted in its calibration cost.
    assert (default["correct"], default["n_fail_open"]) == (10, 0)
