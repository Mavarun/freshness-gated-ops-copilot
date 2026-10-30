"""README Oct 29 section: newest first, and every quoted number matches its artifact."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "artifacts"
README = (ROOT / "README.md").read_text(encoding="utf-8")
HEAD = "## Real-wordlist passphrases (2026-10-29)"
SECTION = README.split(HEAD, 1)[1].split("\n## ", 1)[0]


def _j(name: str) -> dict:
    return json.loads((ART / name).read_text())


def test_section_is_followed_by_the_credited_word_section() -> None:
    heads = [h for h in README.splitlines() if h.startswith("## ")]
    i = next(k for k, h in enumerate(heads) if h.startswith(HEAD))
    assert heads[i + 1].startswith("## Credited-word check (2026-10-28)")


def test_amended_confirm_table_matches() -> None:
    c = _j("passphrase_tail_amended_confirm.json")
    a, b = c["shipped"]["probe"]["total"], c["chosen"]["probe"]["total"]
    assert f"| rows leaking a passphrase word | {a['leak_rows']} / 1,200 | **{b['leak_rows']} / 1,200** |" in SECTION
    assert f"| passphrase words leaked | {a['leak_words']} / {a['words']:,} | **{b['leak_words']} / {b['words']:,}** |" in SECTION
    assert f"| over-redacted template words | {a['over_words']} | {b['over_words']} |" in SECTION
    assert f"| leaks from tail trimming | {c['shipped']['probe']['cause']['tail_trim']} rows | 0 |" in SECTION
    assert "tail_trim" not in c["chosen"]["probe"]["cause"]
    sep = sum(c["shipped"]["probe"]["by_separator"][k]["leak_words"] for k in ("hyphen", "dot", "underscore"))
    sep_now = sum(c["chosen"]["probe"]["by_separator"][k]["leak_words"] for k in ("hyphen", "dot", "underscore"))
    assert f"| hyphen / dot / underscore words leaked | {sep} | {sep_now} (unchanged by design) |" in SECTION
    assert f"{c['se_test_candidates']}" in SECTION and c["chosen"]["se"]["flagged"] == 0


def test_calibration_first_confirm_and_totals_match() -> None:
    cal = {r["arm"]: r for r in _j("passphrase_tail_calibration.json")["results"]}
    assert f"from {cal['trim/none']['probe']['total']['leak_words']} to {cal['keep/0.10']['probe']['total']['leak_words']}" in SECTION
    assert f"from {cal['trim/none']['se']['flagged']} to {cal['keep/0.10']['se']['flagged']}" in SECTION
    conf = _j("passphrase_tail_confirm.json")
    assert f"{conf['shipped']['probe']['total']['leak_words']} → {conf['chosen']['probe']['total']['leak_words']} words" in SECTION
    ev = _j("passphrase_wordlist_eval.json")
    oct29_seeds = [str(x) for x in (2910, 2929, 2931)]
    old = sum(ev["seeds"][k]["oct13"]["leak_words"] for k in oct29_seeds)
    new = sum(ev["seeds"][k]["oct29"]["leak_words"] for k in oct29_seeds)
    assert f"leaked words go {old} → {new}" in SECTION
    fp = _j("passphrase_fp_eval.json")["train"]
    assert f"17 → {fp['flagged']} of {fp['sentences']:,}" in SECTION
