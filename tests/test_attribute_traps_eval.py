"""Attribute-trap CI step: workflow wiring and a byte-stable committed report."""

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_ci_step_is_in_the_workflow():
    wf = (ROOT / ".github" / "workflows" / "eval.yml").read_text(encoding="utf-8")
    assert "python scripts/run_attribute_traps_eval.py" in wf and "artifacts/attribute_traps_eval.json" in wf


def test_committed_report_matches_a_fresh_run():
    committed = json.loads((ROOT / "artifacts" / "attribute_traps_eval.json").read_text())
    subprocess.run([sys.executable, str(ROOT / "scripts" / "run_attribute_traps_eval.py")], check=True,
                   capture_output=True, text=True)
    fresh = json.loads((ROOT / "artifacts" / "attribute_traps_eval.json").read_text())
    assert fresh == committed
    assert fresh["shipped_default"]["opened"] == []
    assert fresh["pre_change_default"]["opened"] == ["at-01", "at-07", "at-12", "at-21", "at-22", "at-25", "at-33"]
    assert fresh["split_sizes"] == {"tune": 18, "confirm": 18} and fresh["heldout_words_in_file"] == []
