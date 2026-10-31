"""README Oct 31 section: newest first, and every quoted number matches its artifact."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "artifacts"
README = (ROOT / "README.md").read_text(encoding="utf-8")
HEAD = "## Glued-digit guard (2026-10-31)"
SECTION = README.split(HEAD, 1)[1].split("\n## ", 1)[0]


def _j(name: str) -> dict:
    return json.loads((ART / name).read_text())


def test_section_is_first_then_oct30() -> None:
    heads = [h for h in README.splitlines() if h.startswith("## ")]
    assert heads[0].startswith(HEAD) and heads[1].startswith("## Passphrase list arm and purpose-number fix (2026-10-30)")


def test_confirm_table_and_intro() -> None:
    c = _j("passphrase_dictionary_confirm.json")
    base, res = c["results"]
    a, b = base["probe"]["attached"]["total"], res["probe"]["attached"]["total"]
    assert f"| glued-digit rows leaking a passphrase word | {a['leak_rows']} / 1,200 | **{b['leak_rows']} / 1,200** |" in SECTION
    assert f"| glued-digit passphrase words leaked | {a['leak_words']:,} / {a['words']:,} | **{b['leak_words']} / {b['words']:,}** |" in SECTION
    st = [r["probe"]["standard"]["total"]["leak_words"] for r in (base, res)]
    assert f"| Oct 29-shape words leaked | {st[0]} | {st[1]} |" in SECTION
    ov = [sum(r["probe"][k]["total"]["over_words"] for k in ("standard", "attached", "invented")) for r in (base, res)]
    assert f"| over-redacted template words (three probes) | {ov[0]:,} | {ov[1]:,} |" in SECTION
    assert f"| SE test identifiers flagged (new) | {base['se']['ident_flagged']} / {c['se_identifiers']} | " \
           f"{res['se']['ident_flagged']} / {c['se_identifiers']} ({res['se']['ident_new']}) |" in SECTION
    assert f"{b['leak_words']} of {b['words']:,} words leak on the Oct 31 fresh confirm seed ({a['leak_words']:,} with the Oct 30" in README
    off = c["offlist"]
    assert f"({off['ops/compounds/off']['leak_words']} → {off['ops/compounds/guard']['leak_words']} of {off['ops/compounds/off']['words']:,})" in SECTION
    assert all(res["checks"].values()) and len(res["checks"]) == 9 and "All nine checks pass" in SECTION


def test_calibration_numbers() -> None:
    cal = {r["arm"]: r for r in _j("passphrase_dictionary_calibration.json")["results"]}
    assert cal["ops/compounds/raw"]["se"]["ident_new"] == 12 and "newly flags 12 SE train" in SECTION
    g = (cal["ops/compounds/off"]["probe"]["attached"]["total"]["leak_words"], cal["ops/compounds/guard"]["probe"]["attached"]["total"]["leak_words"])
    assert f"words {g[0]:,} → {g[1]}" in SECTION
    inv = (cal["dict/compounds/off"]["probe"]["invented"]["total"], cal["dict_cv/compounds/off"]["probe"]["invented"]["total"])
    assert f"`dict` leaks {inv[0]['leak_words']:,} and\n   `dict_cv` {inv[1]['leak_words']} of {inv[0]['words']:,} invented words" in SECTION


def test_ci_and_posthoc_numbers() -> None:
    ev = _j("passphrase_wordlist_eval.json")["oct31"]
    g = [k for k in ev if k.startswith("glued-")]
    assert len(g) == 4
    assert f"leak {sum(ev[k]['shipped']['leak_words'] for k in g)} words together ({sum(ev[k]['oct30']['leak_words'] for k in g):,} with" in SECTION
    ph = _j("passphrase_dictionary_posthoc.json")
    s = ph["se_train"]
    assert f"stops flagging {s['dict/compounds/guard']['dropped']} of {s['shipped_flags']} identifiers" in SECTION
    assert f"cut it to {s['dict/compounds/guard']['still_flagged']}" in SECTION
    c = ph["invented"]["3121"]
    assert f"({c['dict/compounds/guard']['cv']['total']['leak_words']} → {c['dict_cv/compounds/guard']['cv']['total']['leak_words']} words on seed 3121)" in SECTION
    assert f"closed-syllable half ({c['dict_cv/compounds/guard']['cvc']['total']['leak_words']})" in SECTION
