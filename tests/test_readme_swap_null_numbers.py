"""Numbers quoted in the README's swap null section match the committed artifacts."""

import json
from pathlib import Path

from ops_copilot.config import CopilotConfig

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "artifacts"
HEAD = "## Random one-word swaps on answered questions (2026-11-07)"


def _section() -> str:
    text = (ROOT / "README.md").read_text(encoding="utf-8")
    start = text.index(HEAD)
    return text[start: text.index("\n## ", start + 5)]


def _j(name: str) -> dict:
    return json.loads((ART / name).read_text(encoding="utf-8"))


def test_it_is_the_newest_section():
    heads = [h for h in (ROOT / "README.md").read_text(encoding="utf-8").splitlines() if h.startswith("## ")]
    # newest until the 2026-11-09 non-key coverage section went above it
    assert heads[1].startswith(HEAD) and heads[0].startswith("## Non-key coverage rule")


def test_calibration_table_matches():
    cal, s = _j("swap_null_calibration.json"), _section()
    assert cal["picked"] == "known_off" and cal["swaps"] == 384
    ref = cal["arms"]["shipped"]
    for name in ("shipped", "known_off", "sense_all", "sense_known", "credit_rank5"):
        a = cal["arms"][name]
        cells = (f"| {a['passed']} | {a['rates']['null_pass_rate']:.3f} | {a['by_mechanism']['passage']} | "
                 f"{ref['answered'] - a['answered']} |")
        assert cells in s, name


def test_confirm_table_and_ship_call_match():
    c, s = _j("swap_null_confirm.json"), _section()
    assert c["ships"] is True and c["arm"] == "known_off" and c["swaps"] == 459
    sh, ko = c["arms"]["shipped"], c["arms"]["known_off"]
    assert f"| {sh['passed']} | {sh['rates']['null_pass_rate']:.3f} |" in s
    assert f"| {ko['passed']} | **{ko['rates']['null_pass_rate']:.3f}** | {ko['answered']} of {sh['answered']} |" in s
    assert c["trap_opens"] == {"shipped": 0, "known_off": 0}
    assert f"{sh['rates']['null_pass_rate']:.3f} → {ko['rates']['null_pass_rate']:.3f}" in s
    assert CopilotConfig().passage_support_known_words is False


def test_costs_and_residual_match():
    rob, rep, s = _j("robustness_metrics.json"), _j("swap_null_report.json"), _section()
    assert f"0.901 → {rob['perturbed_accuracy']:.3f}" in s
    assert f"{rep['passed']} of {rep['swaps']} calibration" in s
    assert f"In {rep['by_mechanism']['unsupported']} of them" in s
