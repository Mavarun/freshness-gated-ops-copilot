"""README Oct 30 section: newest first, and every quoted number matches its artifact."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "artifacts"
README = (ROOT / "README.md").read_text(encoding="utf-8")
HEAD = "## Passphrase list arm and purpose-number fix (2026-10-30)"
SECTION = README.split(HEAD, 1)[1].split("\n## ", 1)[0]


def _j(name: str) -> dict:
    return json.loads((ART / name).read_text())


def test_section_is_first_then_oct29() -> None:
    heads = [h for h in README.splitlines() if h.startswith("## ")]
    assert heads[0].startswith(HEAD) and heads[1].startswith("## Real-wordlist passphrases (2026-10-29)")


def test_confirm_table_and_intro() -> None:
    c = _j("passphrase_compound_confirm.json")
    a, b = c["results"][0]["probe"]["total"], c["results"][1]["probe"]["total"]
    assert f"| rows leaking a passphrase word | {a['leak_rows']} / 1,200 | **{b['leak_rows']} / 1,200** |" in SECTION
    assert f"| passphrase words leaked | {a['leak_words']} / {a['words']:,} | **{b['leak_words']} / {b['words']:,}** |" in SECTION
    assert f"| over-redacted template words | {a['over_words']} | {b['over_words']} |" in SECTION
    assert f"{c['se_identifiers']} (`{c['results'][1]['idents']['new_examples'][0]}`)" in SECTION
    assert f"{b['leak_words']} of {b['words']:,} words leak on the Oct 30 fresh confirm seed ({a['leak_words']} with" in README


def test_calibration_posthoc_and_ci_numbers() -> None:
    cal = {r["arm"]: r for r in _j("passphrase_compound_calibration.json")["results"]}
    assert f"from {cal['none/-/-']['probe']['total']['leak_words']} to {cal['all4/space/num']['probe']['total']['leak_words']}" in SECTION
    assert f"newly flag {cal['but1_4/-/-']['idents']['new_flags']} and {cal['all3/-/-']['idents']['new_flags']} SE train" in SECTION
    ph = _j("passphrase_compound_posthoc.json")
    at = ph["attribution"]
    assert f"({at['none/-/-']['confirm']['leak_words']} → {at['none/-/num']['confirm']['leak_words']} alone)" in SECTION
    assert f"{at['none/-/-']['confirm']['leak_words']} → {at['all4/-/-']['confirm']['leak_words']}." in SECTION
    assert f"({at['none/-/-']['offlist']['leak_words']} → {at['all4/space/num']['offlist']['leak_words']} with or without" in SECTION
    g = ph["attached"]["shipped"]["total"]
    assert f"leak {g['leak_words']:,} of {g['words']:,} words ({g['leak_rows']} of 1,200 rows)" in SECTION
    ev = _j("passphrase_wordlist_eval.json")["seeds"]
    k = ("2910", "2929", "2931")
    assert f"leak {sum(ev[x]['shipped']['leak_words'] for x in k)} words together ({sum(ev[x]['oct29']['leak_words'] for x in k)} with" in SECTION


def test_digit_check_numbers() -> None:
    d = _j("passphrase_digit_check.json")
    a, tr, te = d["attached"], d["se"]["train"], d["se"]["test"]
    assert f"**{a['shipped']['leak_words']:,} → {a['candidate']['leak_words']}**" in SECTION
    assert f"({a['shipped']['leak_rows']} → {a['candidate']['leak_rows']} rows; over-redacted {a['shipped']['over_words']} → {a['candidate']['over_words']})" in SECTION
    assert f"**{tr['ident_new']} of {tr['n_identifiers']:,} SE train identifiers**" in SECTION
    assert f"{te['ident_new']} of {te['n_identifiers']} in test" in SECTION
    assert f"SE sentences {tr['sent_shipped']} → {tr['sent_candidate']} train / {te['sent_shipped']} → {te['sent_candidate']} test" in SECTION
    assert d["ships"] is False and "**ships off**" in SECTION


def test_weakness_base_rate() -> None:
    cal = _j("passphrase_compound_calibration.json")
    n, f = cal["se_identifiers"], cal["shipped_identifier_flags"]
    assert f"{f} of {n:,} ({100 * f / n:.1f}%)" in SECTION
