"""Post-hoc veto audit and the README section, pinned to the artifacts."""

import json
from pathlib import Path

from ops_copilot.credit_check_audit import effect

ROOT = Path(__file__).resolve().parents[1]
AUD = json.loads((ROOT / "artifacts" / "credit_check_audit.json").read_text())
CAL = json.loads((ROOT / "artifacts" / "credit_check_calibration.json").read_text())
CON = json.loads((ROOT / "artifacts" / "credit_check_confirm.json").read_text())


def _section() -> str:
    s = (ROOT / "README.md").read_text(encoding="utf-8")
    start = s.index("## Credited-word check (2026-10-28)")
    return s[start:s.index("\n## ", start + 10)]


def test_effect_labels():
    assert effect("REFUSE_UNGROUNDED", "ANSWER", "REFUSE_UNGROUNDED") == "closed"
    assert effect("ANSWER", "ANSWER", "REFUSE_UNGROUNDED") == "lost"
    assert effect("REFUSE_PII", "REFUSE_PII", "REFUSE_UNGROUNDED") == "lost"
    assert effect("ANSWER", "REFUSE_STALE", "REFUSE_UNGROUNDED") == "relabelled"
    assert effect("ANSWER", "ANSWER", "ANSWER") == "none"


def test_audit_vetoes():
    assert AUD["n_rows"] == 396 and AUD["n_vetoed_rows"] == 14
    assert AUD["by_effect"] == {"closed": 1, "lost": 5, "none": 8}
    by = {v["id"]: v for v in AUD["vetoes"]}
    assert by["at2-01"]["effect"] == "closed" and by["at2-01"]["credits"] == ["taste <- one"]
    lost = sorted(v["id"] for v in AUD["vetoes"] if v["effect"] == "lost")
    # the four calibration losses plus the fresh-set label
    assert lost == sorted(CAL["chosen"]["new_errors"] + ["f13"])
    assert [by[i]["credits"] for i in ("d3-02", "d5-18", "d6-09")] == [
        ["today <- only"], ["gap <- only"], ["available <- already"]]
    assert all(v["now"] != "ANSWER" or v["expect"] == "ANSWER" for v in AUD["vetoes"])


def test_readme_section_quotes_the_artifacts():
    s = _section()
    ch, b = CAL["chosen"], CAL["baseline_shipped"]
    assert f"{CAL['n_safe']} of {CAL['n_settings']} arms are safe" in s
    assert f"{ch['calib_correct']} vs {b['correct']} of {CAL['n_rows']} (ANSWER {ch['calib_answer_correct']} vs " \
           f"{b['answer_correct']})" in s
    d7 = CON["dev7_confirm"]
    assert f"| dev7 confirm correct / ANSWER | {d7['shipped']['correct']} / 18, {d7['shipped']['answer_correct']} of 13 | " \
           f"{d7['arm']['correct']} / 18, {d7['arm']['answer_correct']} of 13 |" in s
    assert "| v3 confirm traps opened | 0 / 19 | 0 / 19 |" in s
    assert f"{AUD['n_vetoed_rows']} rows have a\n   veto" in s
    assert "**v2 traps go from 1 of 40 open to 0 of 40**" in s
    assert "ships on" in s.splitlines()[0]
