"""README Nov 1 section: newest first, and every quoted number matches its artifact."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "artifacts"
README = (ROOT / "README.md").read_text(encoding="utf-8")
HEAD = "## Shape guards (2026-11-01)"
SECTION = README.split(HEAD, 1)[1].split("\n## ", 1)[0]


def _j(name: str) -> dict:
    return json.loads((ART / name).read_text())


def test_section_follows_function_parts_and_precedes_oct31() -> None:
    heads = [h for h in README.splitlines() if h.startswith("## ")]
    i = next(k for k, h in enumerate(heads) if h.startswith(HEAD))
    assert heads[i + 1].startswith("## Glued-digit guard (2026-10-31)")


def test_calibration_numbers_match() -> None:
    cal = _j("passphrase_shape_calibration.json")
    r = {x["arm"]: x for x in cal["results"]}
    assert cal["chosen"] == "case+tld"
    assert r["shipped"]["se"]["ident_flagged"] == 221 and cal["se_identifiers"] == 1920
    assert f"`case` 221 → {r['case']['se']['ident_flagged']}" in SECTION
    assert f"`tld` → {r['tld']['se']['ident_flagged']}" in SECTION
    assert f"`case+tld` → **{r['case+tld']['se']['ident_flagged']}**" in SECTION
    assert f"`case+tld+stop` → {r['case+tld+stop']['se']['ident_flagged']}" in SECTION
    ph0 = r["shipped"]["probe"]["phrase"]["total"]
    ph1 = r["case+tld+stop"]["probe"]["phrase"]["total"]
    assert f"({ph0['leak_words']:,} → {ph1['leak_words']:,} of {ph0['words']:,}; budget {int(0.005 * ph0['words'])})" in SECTION
    assert not all(r["case+tld+stop"]["safe"].values()) and all(r["case+tld"]["safe"].values())


def test_confirm_table_matches() -> None:
    c = _j("passphrase_shape_confirm.json")
    base, res = c["results"]
    assert c["ships"] and all(res["checks"].values())
    n = c["se_identifiers"]
    assert f"| {base['se']['ident_flagged']} / {n} | **{res['se']['ident_flagged']} / {n}** (0 new) |" in SECTION
    lw = lambda r: " / ".join(f"{r['probe'][k]['total']['leak_words']:,}" for k in ("standard", "attached", "invented", "cased", "phrase"))
    assert f"| {lw(base)} | {lw(res)} |" in SECTION
    over = lambda r: sum(r["probe"][k]["total"]["over_words"] for k in r["probe"])
    assert f"| {over(base):,} | {over(res):,} |" in SECTION
    off = c["offlist"]
    assert f"| {off['shipped']['leak_words']} / {off['shipped']['words']:,} | {off['case+tld']['leak_words']} / {off['case+tld']['words']:,} |" in SECTION
