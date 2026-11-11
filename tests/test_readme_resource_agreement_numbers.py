"""Numbers quoted in the README's resource-agreement section match the committed artifacts."""

import json
from pathlib import Path

from ops_copilot.config import CopilotConfig

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "artifacts"
HEAD = "## Resource agreement for ops synonyms (2026-11-11)"


def _section() -> str:
    text = (ROOT / "README.md").read_text(encoding="utf-8")
    start = text.index(HEAD)
    return text[start: text.index("\n## ", start + 5)]


def _j(name: str) -> dict:
    return json.loads((ART / name).read_text(encoding="utf-8"))


def test_it_is_the_newest_section():
    heads = [h for h in (ROOT / "README.md").read_text(encoding="utf-8").splitlines() if h.startswith("## ")]
    assert heads[0].startswith(HEAD)


def test_calibration_table_matches():
    cal, s = _j("resource_agreement_calibration.json"), _section()
    ref = cal["arms"]["shipped"]
    for name, a in cal["arms"].items():
        label = "shipped" if name == "shipped" else f"`{name}`"
        c = cal["citation"].get(name, {"new_wrong": [], "budget_lost": 0})
        row = (f"| {label} | {a['passed']} | {a['rates']['null_pass_rate']:.3f} | {a['answered'] - ref['answered']:+d} | "
               f"{a['refuse_opened']} of {a['n_refuse_rows']} | {len(c['new_wrong'])} | {c['budget_lost']} |")
        assert row in s, name
    assert cal["picked"] is None and "ships off" in s.splitlines()[0] and "dev10 stays unseen" in s.splitlines()[0]
    assert f"({cal['rows']} rows)" in s and f"same {cal['swaps']}" in s
    rates = sorted(a["rates"]["null_pass_rate"] for n, a in cal["arms"].items() if n in ("agree2_lone", "agree2_all", "agree3_all"))
    assert f"{ref['rates']['null_pass_rate']:.3f} → {rates[0]:.3f}-{rates[-1]:.3f}" in s.splitlines()[0]


def test_posthoc_table_matches():
    cov, s = _j("resource_agreement_posthoc.json")["coverage"], _section()
    for split, label in (("dev", "dev"), ("heldout", "held-out")):
        m = cov[split]["summary"]
        assert f"| {label} | {m['pairs']} | {m['gold_2plus']} | {m['top2_is_gold']} | {m['top2_is_wrong']} |" in s


def test_knob_ships_off():
    assert CopilotConfig().use_resource_agreement is False
