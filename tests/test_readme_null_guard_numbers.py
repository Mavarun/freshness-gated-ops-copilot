"""The 2026-10-25 README section quotes numbers that must match the committed artifacts."""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
README = (ROOT / "README.md").read_text()
SECTION = README.split("## Null-control test on passage rescues (2026-10-25)")[1].split("\n## ")[0]


def _j(name):
    return json.loads((ROOT / "artifacts" / name).read_text())


def test_section_is_first_and_quotes_confirm_numbers():
    first = [l for l in README.splitlines() if l.startswith("## ")][0]
    assert first.startswith("## Null-control test on passage rescues (2026-10-25)")
    conf = _j("passage_null_confirm.json")
    assert conf["decision"]["default_on"] is True
    for s in ("**0 / 18**", "8 / 20 | 7 / 20 (d5-13 lost)", "3 / 12 | 2 / 12", "0 / 9 | 0 / 9",
              "1.000 / 0.902 / 0.514"):
        assert s in SECTION


def test_section_quotes_calibration_and_trap_numbers():
    traps = _j("attribute_traps_eval.json")
    assert traps["pre_change_default"]["n_opened"] == 7 and traps["shipped_default"]["n_opened"] == 0
    assert "**The pre-change default opens 7 of 36**" in SECTION
    assert "**0 of 5 safe.**" in SECTION and "93 vs 92 of 171" in SECTION
    assert "**q = 0.30 is the one safe setting**" in SECTION and "88 vs 92 of 171" in SECTION
    assert "42 of 48" in SECTION and "98 vs 88 of 171 (ANSWER 33 vs 24)" in SECTION
    assert "drops 14 to 11 of 26" in SECTION and "**0 of 9**" in SECTION
