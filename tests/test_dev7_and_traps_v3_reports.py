"""CI report steps for the spent dev7 set and the v3 traps: frozen, reproducible, pinned."""

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _fresh(script: str, artifact: str) -> tuple[dict, dict]:
    committed = json.loads((ROOT / "artifacts" / artifact).read_text())
    subprocess.run([sys.executable, str(ROOT / "scripts" / script)], check=True, capture_output=True, text=True)
    return committed, json.loads((ROOT / "artifacts" / artifact).read_text())


def test_steps_are_in_the_workflow():
    wf = (ROOT / ".github" / "workflows" / "eval.yml").read_text(encoding="utf-8")
    for s, a in (("run_dev7_eval.py", "synonym_dev7_eval.json"),
                 ("run_attribute_traps_v3_eval.py", "attribute_traps_v3_eval.json")):
        assert f"python scripts/{s}" in wf and f"artifacts/{a}" in wf


def test_dev7_report_matches_a_fresh_run_and_pins_the_shipped_default():
    committed, fresh = _fresh("run_dev7_eval.py", "synonym_dev7_eval.json")
    assert fresh == committed
    assert fresh["vocabulary_problems"] == {} and fresh["heldout_words_in_file"] == []
    assert fresh["split_sizes"] == {"tune": 22, "confirm": 18} and fresh["n_must_refuse"] == 13
    t, c = fresh["default"]["tune"], fresh["default"]["confirm"]
    assert (t["correct"], t["answer_correct"], c["correct"], c["answer_correct"]) == (5, 1, 5, 2)
    assert t["must_refuse_opened"] == c["must_refuse_opened"] == []
    # agrees with the one-shot confirm's arm (the confirm ran before the flip)
    arm = json.loads((ROOT / "artifacts" / "credit_check_confirm.json").read_text())["dev7_confirm"]["arm"]
    assert arm["decisions"] == c["decisions"]


def test_traps_v3_report_matches_a_fresh_run_and_has_no_power_yet():
    committed, fresh = _fresh("run_attribute_traps_v3_eval.py", "attribute_traps_v3_eval.json")
    assert fresh == committed
    assert fresh["split_sizes"] == {"tune": 19, "confirm": 19} and fresh["heldout_words_in_file"] == []
    # honest reading: even the pre-change default refuses all 38, so v3 cannot
    # show a benefit of the credited-word check, only the absence of harm
    for arm in fresh["arms"].values():
        assert arm["n_opened"] == 0 and arm["n"] == 38
