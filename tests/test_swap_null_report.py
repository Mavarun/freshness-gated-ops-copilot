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
    # 42 of 384 under the Nov 7 default; the non-key rule (Nov 17) refuses every swap whose
    # word is supported nowhere, which was the largest residual (24 non-key / unsupported / apart)
    assert (fresh["swaps"], fresh["passed"], fresh["ceiling"]) == (384, 14, 42)
    assert fresh["by_mechanism"] == {"passage": 0, "translation": 0, "semantic": 0, "lexical": 14, "unsupported": 0}
    assert not any("unsupported" in k for k in fresh["residual"])
    # what is left is lexical: the swapped word is in the evidence, mostly in the key half
    assert fresh["residual"] == {"key / lexical / apart": 6, "key / lexical / same sentence": 4,
                                 "non-key / lexical / apart": 1, "non-key / lexical / same sentence": 3}
    assert fresh["problems"] == []


def test_ceiling_matches_the_protocol_calibration():
    cal = json.loads((ROOT / "artifacts" / "swap_null_calibration.json").read_text())
    assert cal["picked"] == "known_off" and cal["arms"]["known_off"]["passed"] == 42
