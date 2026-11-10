"""Numbers quoted in the README's non-key coverage section match the committed artifacts."""

import json
from pathlib import Path

from ops_copilot.config import CopilotConfig

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "artifacts"
HEAD = "## Non-key coverage rule (2026-11-09)"


def _section() -> str:
    text = (ROOT / "README.md").read_text(encoding="utf-8")
    start = text.index(HEAD)
    return text[start: text.index("\n## ", start + 5)]


def _j(name: str) -> dict:
    return json.loads((ART / name).read_text(encoding="utf-8"))


def test_section_order():
    heads = [h for h in (ROOT / "README.md").read_text(encoding="utf-8").splitlines() if h.startswith("## ")]
    assert heads[1].startswith(HEAD) and heads[0].startswith("## Compound parts for the non-key rule")


def test_calibration_table_matches():
    cal, s = _j("nonkey_calibration.json"), _section()
    ref = cal["arms"]["shipped"]
    for name in ("all", "corpus", "idf_q25", "idf_q50", "cov_065"):
        a = cal["arms"][name]
        cells = (f"| {a['passed']} | {a['rates']['null_pass_rate']:.3f} | {a['by_mechanism']['unsupported']} | "
                 f"{ref['answered'] - a['answered']} |")
        assert cells in s, name
    assert f"| shipped | {ref['passed']} | {ref['rates']['null_pass_rate']:.3f} | 25 | 0 |" in s


def test_confirm_table_and_ship_call_match():
    c, s = _j("nonkey_confirm.json"), _section()
    sh, a = c["arms"]["shipped"], c["arms"]["all"]
    assert f"| shipped | {c['swaps']} | {sh['passed']} | {sh['rates']['null_pass_rate']:.3f} |" in s
    assert f"| `all` | {c['swaps']} | {a['passed']} | **{a['rates']['null_pass_rate']:.3f}** |" in s
    assert f"{a['answered']} of {sh['answered']}" in s
    assert f"{len(c['topic_trap_opens']['shipped'])} of 16" in s and f"**{len(c['topic_trap_opens']['all'])} of 16**" in s
    assert c["ships"] is False and "ships off" in s.splitlines()[0]
    assert CopilotConfig().grounding_nonkey_rule == "off"


def test_posthoc_and_dev8_numbers_match():
    p, d, s = _j("nonkey_posthoc.json"), _j("dev8_eval.json"), _section()
    assert p["lost_compound_part"] == 2 and "2 of\nthe 5 rows" in s
    assert len(d["arms"]["shipped"]["traps_open"]) == 5 and "answers 5 of the 16" in s
