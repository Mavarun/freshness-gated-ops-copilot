import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_dev8_report_runs_clean_and_matches_the_confirm():
    r = subprocess.run([sys.executable, str(ROOT / "scripts/run_dev8_eval.py")], capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr
    rep = json.loads((ROOT / "artifacts/dev8_eval.json").read_text(encoding="utf-8"))
    conf = json.loads((ROOT / "artifacts/nonkey_confirm.json").read_text(encoding="utf-8"))
    assert rep["problems"] == [] and rep["heldout_words_in_file"] == []
    assert rep["arms"]["shipped"]["answered"] == conf["dev8_answered"]["shipped"] == 20
    assert rep["arms"]["all (off)"]["answered"] == conf["dev8_answered"]["all"] == 17
    assert rep["arms"]["shipped"]["traps_open"] == conf["topic_trap_opens"]["shipped"] == rep["known_open"]
    assert rep["arms"]["all (off)"]["traps_open"] == conf["topic_trap_opens"]["all"]
