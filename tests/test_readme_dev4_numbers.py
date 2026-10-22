"""Numbers quoted in the README's dev4 section match the committed artifacts."""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "artifacts"


def _section() -> str:
    text = (ROOT / "README.md").read_text(encoding="utf-8")
    start = text.index("## Unknown-words-only Datamuse on a fresh dev4 set (2026-10-22)")
    return text[start: text.index("\n## ", start + 5)]


def test_confirm_table_rows_match_the_artifact():
    c = json.loads((ART / "datamuse_dev4_confirm.json").read_text())
    s = _section()
    for arm, bold in (("off", False), ("on", True)):
        conf, rob = c["confirm"][arm], c["robustness"][arm]
        h = rob["per_synonym_split"]["heldout"]
        a, b = (f"**{conf['correct']}/{conf['n']}**", f"**{conf['answer_correct']}/{conf['n_answer']}**") if bold \
            else (f"{conf['correct']}/{conf['n']}", f"{conf['answer_correct']}/{conf['n_answer']}")
        cells = (f"| {a} | {b} |", f"| {rob['clean_accuracy']:.3f} | {rob['perturbed_accuracy']:.4f} | "
                 f"{h['perturbed_accuracy']:.3f} | {h['by_gate']['ANSWER']['correct']}/9 | "
                 f"{c['fresh'][arm]['accuracy']:.3f} |")
        for cell in cells:
            assert cell in s, (arm, cell)
    for ref in c["reference_arms"].values():
        r = ref["confirm"]
        assert f"| {r['correct']}/{r['n']} | {r['answer_correct']}/{r['n_answer']} | d4-37 | d4-37 |" in s
        assert f"| {ref['fresh']['accuracy']:.3f} |" in s
    failed = sorted(k for k, v in c["decision"]["checks"].items() if not v)
    assert failed == ["confirm_must_refuse_held", "confirm_no_fail_open_write_pii", "confirm_no_new_error"]
    for k in failed:
        assert f"`{k}`" in s
    assert "**The flag\n   ships off**" in s and c["decision"]["default_on"] is False


def test_calibration_numbers_match():
    cal = json.loads((ART / "datamuse_dev4_calibration.json").read_text())
    s = _section()
    ch = cal["chosen"]
    assert f"{cal['n_safe']} of {cal['n_settings']} safe" in s
    assert f"({ch['calib_correct']}/{cal['n_rows']} vs {cal['baseline_off']['correct']}/{cal['n_rows']} off)" in s
    assert f"rank ≤ {ch['max_rank']},\n   two neighbours, context ≥ {ch['context_min']}" in s
    top = max(r["calib_correct"] for r in cal["results"])
    assert f"up to {top}/{cal['n_rows']}" in s


def test_dev4_report_numbers_match():
    rep = json.loads((ART / "synonym_dev4_eval.json").read_text())
    d = rep["halves"]["tune"]["default (shipped)"]
    assert f"**0 of {d['n_answer']}** dev4-tune ANSWER" in _section() and d["answer_correct"] == 0
