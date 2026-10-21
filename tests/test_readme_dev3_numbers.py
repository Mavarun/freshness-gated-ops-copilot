"""Numbers quoted in the README's dev3 section match the committed artifacts."""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "artifacts"


def _section() -> str:
    text = (ROOT / "README.md").read_text(encoding="utf-8")
    start = text.index("## Context-gated Datamuse on a fresh dev3 set (2026-10-21)")
    return text[start: text.index("\n## ", start + 5)]


def test_confirm_table_row_matches_the_artifact():
    c = json.loads((ART / "datamuse_dev3_confirm.json").read_text())
    on, off = c["confirm"]["on"], c["confirm"]["off"]
    rob = c["robustness"]["on"]
    h = rob["per_synonym_split"]["heldout"]
    row = (f"| dev3-chosen | **{on['correct']}/{on['n']}** | **{on['answer_correct']}/{on['n_answer']}** | 0 | "
           f"1.000 | {rob['perturbed_accuracy']:.4f} | {h['perturbed_accuracy']:.3f} | "
           f"**{h['by_gate']['ANSWER']['correct']}/9** | {c['fresh']['on']['accuracy']:.3f} |")
    s = _section()
    assert row in s
    assert f"| off (shipped) | {off['correct']}/{off['n']} | {off['answer_correct']}/{off['n_answer']} |" in s


def test_calibration_and_sweep_numbers_match():
    cal = json.loads((ART / "datamuse_dev3_calibration.json").read_text())
    sw = json.loads((ART / "datamuse_dev3_safety_sweep.json").read_text())
    s = _section()
    assert f"{cal['n_safe']} of {cal['n_settings']} safe" in s
    assert f"({cal['chosen']['calib_correct']}/{cal['n_rows']} vs {cal['baseline_off']['correct']}/{cal['n_rows']} off)" in s
    assert f"all {sw['n_queries']} query literals" in s
    assert f"{len(sw['changed'])} decisions change, {sw['n_opened']} go from a" in s
    assert "**`use_datamuse_ml` stays\n   False**" in s


def test_posthoc_numbers_match():
    unk = json.loads((ART / "datamuse_dev3_posthoc.json").read_text())["arms"]["dev3-chosen, unknown words only"]
    s = _section()
    assert f"It scores {unk['calib']} on calibration and {unk['confirm']} (ANSWER {unk['confirm_answer']})" in s
    assert f"held-out {unk['heldout']:.3f} but ANSWER **{unk['heldout_answer']}/9**" in s
