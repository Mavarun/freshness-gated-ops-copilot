"""README Nov 1 function-parts section: newest first, every quoted number matches its artifact."""

from __future__ import annotations

import json
from pathlib import Path

from ops_copilot.passphrase import FUNCTION_WORDS

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "artifacts"
README = (ROOT / "README.md").read_text(encoding="utf-8")
HEAD = "## Function-word parts (2026-11-01, second slice)"
SECTION = README.split(HEAD, 1)[1].split("\n## ", 1)[0]
COMPOUND = ("dot", "hyphen", "underscore")


def _j(name: str) -> dict:
    return json.loads((ART / name).read_text())


def test_section_order() -> None:
    heads = [h for h in README.splitlines() if h.startswith("## ")]
    i = next(k for k, h in enumerate(heads) if h.startswith(HEAD))
    assert heads[i - 1].startswith("## Space-joined phrases (2026-11-04)") and heads[i + 1].startswith("## Shape guards (2026-11-01)")


def test_calibration_numbers() -> None:
    c = _j("passphrase_phrase_calibration.json")
    base, res = c["results"]
    assert c["passes"]
    b, r = base["probe"]["phrase"], res["probe"]["phrase"]
    assert f"phrase leaked words {b['total']['leak_words']:,} → {r['total']['leak_words']:,} of\n   {b['total']['words']:,}" in SECTION
    for k in ("dot", "hyphen", "underscore", "space"):
        assert f"{k} {b['by_separator'][k]['leak_words']} → {r['by_separator'][k]['leak_words']}" in SECTION
    assert f"{base['se']['ident_flagged']} → {res['se']['ident_flagged']}" in SECTION
    assert res["se"]["ident_new_examples"] == ["WBC_ERR_DOMAIN_NOT_FOUND"]
    assert f"fixed list of {len(FUNCTION_WORDS)} English function words" in SECTION


def test_confirm_table() -> None:
    c = _j("passphrase_phrase_confirm.json")
    base, res = c["results"]
    assert c["passes"] and all(res["checks"].values())
    b, r = base["probe"]["phrase"], res["probe"]["phrase"]
    assert f"| {b['total']['leak_rows']} / 1,200 | **{r['total']['leak_rows']} / 1,200** |" in SECTION
    assert f"| {b['total']['leak_words']:,} / {b['total']['words']:,} | **{r['total']['leak_words']} / {r['total']['words']:,}** |" in SECTION
    cb = sum(b["by_separator"][k]["leak_words"] for k in COMPOUND)
    cr = sum(r["by_separator"][k]["leak_words"] for k in COMPOUND)
    assert f"| {cb} | **{cr}** |" in SECTION
    lw = lambda x: " / ".join(str(x["probe"][k]["total"]["leak_words"]) for k in ("standard", "attached", "invented", "cased"))
    assert f"| {lw(base)} | {lw(res)} |" in SECTION
    assert f"| {base['se']['ident_flagged']} / 147 | {res['se']['ident_flagged']} / 147 ({res['se']['ident_new']}) |" in SECTION
    assert f"Space-joined phrases still leak** ({r['by_separator']['space']['leak_words']} of the {r['total']['leak_words']}" in SECTION
