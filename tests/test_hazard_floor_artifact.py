"""The committed hazard-floor artifact is what a fresh run of the pre-registered rule gives."""

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ART_PATH = ROOT / "artifacts" / "hazard_floor.json"
ART = json.loads(ART_PATH.read_text())


def test_fresh_run_matches():
    subprocess.run([sys.executable, str(ROOT / "scripts/run_hazard_floor_protocol.py")], check=True, capture_output=True)
    assert json.loads(ART_PATH.read_text()) == ART


def test_decision_and_numbers():
    d = ART["decision"]
    assert d["ship"] and d["regression"]["pass"] and d["confirm"]["pass"]
    reg, con = d["regression"], d["confirm"]
    assert (ART["regression"]["n_rows"], ART["confirm"]["n_rows"]) == (751, 28)
    assert (reg["misfires_all"], reg["misfires_floor"], reg["lost_fixes"], reg["answer_changes"]) == (4, 1, 0, 0)
    assert (con["misfires_all"], con["misfires_floor"], con["lost_fixes"], con["answer_changes"]) == (4, 0, 0, 0)


def test_changed_rows_are_the_off_topic_ones():
    changed = lambda part: sorted(r["id"] for r in ART[part]["notable"] if r["all"] != r["floor"])  # noqa: E731
    assert changed("regression") == ["d2-36", "d3-41", "d5-41"]
    assert changed("confirm") == ["hf-01", "hf-02", "hf-06", "hf-12"]
    assert all(r["coverage"] < 0.30 for r in ART["confirm"]["notable"] if r["all"] != r["floor"])
    left = [r["id"] for r in ART["regression"]["notable"] if r["floor"] != r["expect"] and r["floor"] in ("REFUSE_PII", "REFUSE_CANARY")]
    assert left == ["g50-synonym"]


def test_correct_counts_do_not_move():
    for part, n in (("regression", 510), ("confirm", 18)):
        rows = ART[part]["rows"]
        assert sum(r["expect"] == r["all"] for r in rows) == sum(r["expect"] == r["floor"] for r in rows) == n


def test_confirm_must_refuse_rows_sit_well_above_the_floor():
    via = [b for b in ART["confirm"]["must_refuse_scan_off"] if b["scan_off"] == "REFUSE_UNGROUNDED"]
    assert len(via) == 8 and min(b["coverage"] for b in via) == 0.518
