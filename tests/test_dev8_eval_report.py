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
    pre = rep["arms"]["rule off (pre-Nov 17)"]
    # the Nov 9 confirm's shipped arm is the pre-Nov 17 default
    assert pre["answered"] == conf["dev8_answered"]["shipped"] == 20
    assert pre["traps_open"] == conf["topic_trap_opens"]["shipped"]
    # the Nov 17 default (all + hyphen parts) wins back the two hyphen rows over the Nov 9
    # all arm (17 -> 19 of 32; 20 with the rule off) and opens the same two traps as it
    assert conf["dev8_answered"]["all"] == 17 and rep["arms"]["shipped"]["answered"] == 19
    assert rep["arms"]["shipped"]["traps_open"] == conf["topic_trap_opens"]["all"] == rep["known_open"]
