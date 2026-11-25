"""Numbers in the README's 2026-11-24 hazard band section match the committed artifact."""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
A = json.loads((ROOT / "artifacts" / "hazard_band.json").read_text())["read"]
HEAD = "## Hazard floor in the 0.30-0.50 band (2026-11-24)"


def _section() -> str:
    text = (ROOT / "README.md").read_text(encoding="utf-8")
    start = text.index(HEAD)
    return text[start: text.index("\n## ", start + 5)]


def test_newest_first():
    heads = [h for h in (ROOT / "README.md").read_text(encoding="utf-8").splitlines() if h.startswith("## ")]
    assert heads[2].startswith(HEAD) and heads[3].startswith("## Hazard scan floor and duplicate-question")
    assert f"misfires {A['misfires']['all']} → {A['misfires']['floor']} on a 24-row fresh set" in heads[2]


def test_table_and_claims():
    s = _section()
    for arm in ("all", "off"):
        assert f"| `{arm}` | {A['misfires'][arm]} | {A['correct'][arm]} |" in s
    assert f"| `floor` (shipped) | {A['misfires']['floor']} | {A['correct']['floor']} |" in s
    assert A["lost"] == [] and "0 must-refuse rows lost" in s
    assert A["band_off_topic"] == ["hb-20"] and "Only 1 of 12 off-topic rows (`hb-20`, 0.426)" in s
    assert A["answers"] == ["hb-05"] and "`hb-05` \"Paste the slack token" in s
