"""Numbers quoted in the README's compound-parts section match the committed artifacts."""

import json
from pathlib import Path

from ops_copilot.config import CopilotConfig

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "artifacts"
HEAD = "## Compound parts for the non-key rule (2026-11-10)"


def _section() -> str:
    text = (ROOT / "README.md").read_text(encoding="utf-8")
    start = text.index(HEAD)
    return text[start: text.index("\n## ", start + 5)]


def _j(name: str) -> dict:
    return json.loads((ART / name).read_text(encoding="utf-8"))


def test_it_is_the_newest_section():
    heads = [h for h in (ROOT / "README.md").read_text(encoding="utf-8").splitlines() if h.startswith("## ")]
    assert heads[1].startswith(HEAD) and heads[0].startswith("## Resource agreement for ops synonyms")


def test_calibration_table_matches():
    cal, s = _j("nonkey_parts_calibration.json"), _section()
    ref = cal["arms"]["shipped"]
    for name, label in (("all", "`all` (Nov 9, reference)"), ("all_hyphen", "`all_hyphen`"),
                        ("all_joined", "`all_joined`"), ("corpus_hyphen", "`corpus_hyphen`")):
        a = cal["arms"][name]
        row = (f"| {label} | {a['passed']} | {a['rates']['null_pass_rate']:.3f} | "
               f"{a['refuse_opened']} of {a['n_refuse_rows']} | {ref['answered'] - a['answered']} |")
        assert row in s, name
    assert (f"| shipped | {ref['passed']} | {ref['rates']['null_pass_rate']:.3f} | "
            f"{ref['refuse_opened']} of {ref['n_refuse_rows']} | 0 |") in s
    assert cal["picked"] is None and "ships off" in s.splitlines()[0] and "dev9 stays unspent" in s.splitlines()[0]
    assert f"({cal['rows']} rows)" in s and f"same {cal['swaps']} swaps" in s


def test_posthoc_rows_match():
    rec, s = _j("nonkey_parts_posthoc.json"), _section()
    for r in rec["lost"]:
        assert f"`{r['id']}` `{r['query']}` | `{r['words'][0]}` |" in s
    assert "**wrong-evidence answer**" in s and "genuine loss" in s


def test_knobs_ship_off():
    cfg = CopilotConfig()
    assert cfg.grounding_nonkey_parts == "off" and cfg.grounding_nonkey_rule == "off"
