"""Numbers quoted in the README's dev6 / null-seed section match the committed artifacts."""

import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "artifacts"


def _section() -> str:
    text = (ROOT / "README.md").read_text(encoding="utf-8")
    start = text.index("## Datamuse arm confirmed once on a fresh dev6 set (2026-10-26)")
    return text[start: text.index("\n## ", start + 5)]


def _j(name: str) -> dict:
    return json.loads((ART / name).read_text())


def test_it_directly_follows_the_seed_free_section():
    heads = [h for h in (ROOT / "README.md").read_text(encoding="utf-8").splitlines() if h.startswith("## ")]
    assert heads[1].startswith("## Seed-free null test (2026-10-27)")  # under the 2026-10-28 section
    assert heads[2].startswith("## Datamuse arm confirmed once on a fresh dev6 set (2026-10-26)")


def test_confirm_table_matches():
    c = _j("datamuse_dev6_confirm.json")
    s, cf, r = _section(), c["confirm"], c["robustness"]
    assert f"| dev6 correct | {cf['off']['correct']} / 45 | {cf['on']['correct']} / 45 |" in s
    assert f"| dev6 ANSWER | {cf['off']['answer_correct']} / 24 | {cf['on']['answer_correct']} / 24 |" in s
    assert "| dev6 must-refuse opened | 0 | **1 (d6-36)** |" in s and cf["must_refuse_opened_on"] == ["d6-36"]
    po, pn = r["off"]["perturbed_accuracy"], r["on"]["perturbed_accuracy"]
    assert f"1.000 / {po:.3f} | 1.000 / {pn:.3f} |" in s
    ho, hn = (r[a]["per_synonym_split"]["heldout"] for a in ("off", "on"))
    assert (f"| held-out accuracy / ANSWER | {ho['perturbed_accuracy']:.3f} / {ho['by_gate']['ANSWER']['correct']} of 9 | "
            f"{hn['perturbed_accuracy']:.3f} / {hn['by_gate']['ANSWER']['correct']} of 9 |") in s
    f = c["fresh"]
    assert f"| fresh general-English set | {26 - len(f['off']['wrong'])} / 26 | {26 - len(f['on']['wrong'])} / 26 |" in s
    assert f"p = {c['sign_test_p']:.3f}" in s and c["decision"]["default_on"] is False


def test_posthoc_and_seed_numbers_match():
    s, p = _section(), _j("datamuse_dev6_posthoc.json")
    assert f"{p['n_swap_rows_with_unknown_word']} of {p['n_swap_rows']}" in s
    assert f"only **{p['n_rows_mapped']}** rows" in s
    assert f"{p['n_mappings_right_sense']} mappings are right-sense" in s
    assert f"{p['n_mappings_wrong_sense']} are wrong-sense" in s
    seeds = _j("passage_null_seeds.json")
    pr, sec = seeds["primary"], seeds["secondary_300_controls"]
    assert f"only {pr['n_safe_seeds']} of 20 seeds is safe" in s
    opened = Counter(t for x in pr["seeds"].values() for t in x["traps_opened"])
    assert f"at-22 in {opened['at-22']} seeds, at-12 in {opened['at-12']}" in s
    assert f"Calibration stays at {pr['calib_correct_min']}–{pr['calib_correct_max']} of 171" in s
    o2 = Counter(t for x in sec["seeds"].values() for t in x["traps_opened"])
    assert f"({sec['n_safe_seeds']} of 20 safe, at-22 in {o2['at-22']})" in s
    ev = _j("synonym_dev6_eval.json")["default"]
    # the section quotes the 2026-10-26 default; the report now scores the 2026-10-28
    # default, which loses d6-09 to the credited-word check (one row, one ANSWER)
    assert f"({ev['correct'] + 1}/45, ANSWER\n   {ev['answer_correct'] + 1}/24)" in s
