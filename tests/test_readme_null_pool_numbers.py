"""The 2026-10-27 README section quotes numbers that must match the committed artifacts."""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
README = (ROOT / "README.md").read_text()
HEAD = "## Seed-free null test (2026-10-27)"
SECTION = README.split(HEAD)[1].split("\n## ")[0]


def _j(name):
    return json.loads((ROOT / "artifacts" / name).read_text())


def test_section_is_first_and_followed_by_the_dev6_section():
    heads = [h for h in README.splitlines() if h.startswith("## ")]
    assert heads[0].startswith(HEAD)
    assert heads[1].startswith("## Datamuse arm confirmed once on a fresh dev6 set (2026-10-26)")


def test_exact_distribution_numbers():
    ex = _j("passage_null_exact.json")
    d1, d3 = ex["sample_distribution"]["100"], ex["sample_distribution"]["300"]
    row = (f"| P(no attribute trap opens) | **{d1['p_no_trap_open']:.3f}** | {d3['p_no_trap_open']:.3f} |")
    assert row in SECTION
    assert f"| mean traps opened | {d1['mean_traps_opened']:.2f} | {d3['mean_traps_opened']:.2f} |" in SECTION
    assert (f"{d1['p_open']['at-22']:.3f} / {d1['p_open']['at-12']:.3f} | "
            f"{d3['p_open']['at-22']:.3f} / {d3['p_open']['at-12']:.3f}") in SECTION
    assert f"{d1['correct_mean']:.1f} [{d1['correct_p05_p95'][0]}, {d1['correct_p05_p95'][1]}]" in SECTION
    assert f"{ex['n_live_rows']} of 207 rows" in SECTION and "5,067 pool words" in SECTION


def test_calibration_and_confirm_numbers():
    cal, conf = _j("passage_null_pool_calibration.json"), _j("passage_null_pool_confirm.json")
    ch = cal["chosen"]
    assert f"**Chosen: q = {ch['null_min']:.2f}**" in SECTION
    assert f"at {ch['calib_correct']} vs {cal['baseline_shipped']['correct']} of 171" in SECTION
    assert ", ".join(ch["new_errors"]) in SECTION
    assert f"{cal['n_safe']} of {cal['n_settings']} settings are safe" in SECTION
    assert conf["decision"]["default_on"] is False and "**`passage_support_null_pool` stays False**" in SECTION
    assert "**1 / 20 (at2-01)** | **1 / 20 (at2-01)**" in SECTION
    p = conf["traps_v2_confirm"]["shipped_over_samples"]["p_at_least_one_open"]
    assert f"probability {p:.3f}" in SECTION
    assert "0.514 / 0 of 9 | 0.514 / 0 of 9" in SECTION and "20 / 45 (d6-20 lost)" in SECTION


def test_overlap_numbers():
    ov = _j("passage_null_overlap.json")["profile"]
    assert f"q = {ov['worst_trap_cut']:.3f}" in SECTION
    assert f"{len(ov['keep_rows_below_worst_trap'])} ANSWER rows" in SECTION
    assert ov["free_and_safe_cuts"] == [] and "**no whole-pool cut is both safe and free**" in SECTION
    assert "1 of 40 v2 traps (at2-01" in SECTION
