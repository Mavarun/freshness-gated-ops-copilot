import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_step_is_in_the_workflow():
    wf = (ROOT / ".github" / "workflows" / "eval.yml").read_text(encoding="utf-8")
    assert "python scripts/run_swap_null_report.py" in wf and "artifacts/swap_null_report.json" in wf


def test_committed_report_matches_a_fresh_run_and_pins_the_residual():
    committed = json.loads((ROOT / "artifacts" / "swap_null_report.json").read_text())
    subprocess.run([sys.executable, str(ROOT / "scripts" / "run_swap_null_report.py")], check=True,
                   capture_output=True, text=True)
    fresh = json.loads((ROOT / "artifacts" / "swap_null_report.json").read_text())
    assert fresh == committed
    assert (fresh["swaps"], fresh["passed"], fresh["ceiling"]) == (384, 42, 42)
    assert fresh["by_mechanism"] == {"passage": 0, "translation": 0, "semantic": 0, "lexical": 17, "unsupported": 25}
    # the largest residual: a swapped word outside the key half, supported nowhere
    assert fresh["residual"]["non-key / unsupported / apart"] == 24
    assert fresh["problems"] == []


def test_ceiling_matches_the_protocol_calibration():
    cal = json.loads((ROOT / "artifacts" / "swap_null_calibration.json").read_text())
    assert cal["picked"] == "known_off" and cal["arms"]["known_off"]["passed"] == 42
