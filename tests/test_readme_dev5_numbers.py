"""Numbers quoted in the README's dev5 section match the committed artifacts."""

import gzip
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "artifacts"


def _section() -> str:
    text = (ROOT / "README.md").read_text(encoding="utf-8")
    start = text.index("## Word-meaning gate on a fresh dev5 set (2026-10-24)")
    return text[start: text.index("\n## ", start + 5)]


def test_calibration_numbers_match():
    cal = json.loads((ART / "datamuse_dev5_calibration.json").read_text())
    s, ch, off = _section(), cal["chosen"], cal["baseline_off"]
    assert f"**{cal['n_safe']} of {cal['n_settings']} safe**" in s
    assert f"scores {ch['calib_correct']}/{cal['n_rows']} vs {off['correct']}/{cal['n_rows']} off" in s
    assert f"(ANSWER {ch['calib_answer_correct']}/{off['n_answer']} vs {off['answer_correct']}/{off['n_answer']})" in s
    assert f"context ≥ {ch['context_min']}, sense ≥ {ch['sense_min']:.2f}" in s
    assert cal["baseline_off_opened_must_refuse"] == ["d5-38"] and "d5-38" in s
    assert "42 of 48 arms add no new error" in s
    assert not any("d4-37" in r["must_refuse_opened"] for r in cal["results"])
    assert "stays refused in all 48 arms" in s


def test_probe_numbers_match():
    p = json.loads((ART / "passage_sense_probe.json").read_text())
    s = _section()
    d, c = p["default"], p["sense_check"]
    assert f"**{d['correct']}/{p['n_rows']} to {c['correct']}/{p['n_rows']}**" in s
    assert f"(ANSWER {d['answer_correct']}/{d['n_answer']} to {c['answer_correct']}/{c['n_answer']}, " \
           f"{len(p['new_errors'])} new\n   errors)" in s
    assert f"costs {len(p['new_errors'])} correct calibration rows" in s


def test_pair_table_and_dev5_report_numbers_match():
    s = _section()
    meta = json.loads(gzip.decompress((ROOT / "data" / "datamuse" / "cf_pair_cosine.json.gz").read_bytes()))["meta"]
    assert f"{meta['n_pairs']:,} pairs, {meta['n_missing']:,} of them" in s
    assert f"cover {round(100 * (1 - meta['n_missing'] / meta['n_pairs']))}% of Datamuse pairs" in s
    rep = json.loads((ART / "synonym_dev5_eval.json").read_text())
    # Historical: the section quotes the PR #28 default (10/24, ANSWER 3/13). The
    # report now scores the 2026-10-25 default (null test on), quoted in its own section.
    assert "(10/24, ANSWER 3/13)" in s
    t = rep["tune_default"]
    # 10 / 2 under the 2026-10-25 default; 9 / 1 since the credited-word check
    # (2026-10-28) refuses d5-18 (artifacts/credit_check_calibration.md)
    assert (t["correct"], t["answer_correct"]) == (9, 1)
    assert rep["split_sizes"] == {"tune": 24, "confirm": 20} and "24 `tune` / 20 `confirm`" in s
