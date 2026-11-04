"""README numbers of the Nov 4 space-bridge section are pinned to the committed artifacts."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
README = (ROOT / "README.md").read_text(encoding="utf-8")


def _art(name: str) -> dict:
    return json.loads((ROOT / "artifacts" / name).read_text())


def test_section_exists_and_says_it_ships_off() -> None:
    assert "## Space-joined phrases (2026-11-04)" in README and "so it ships off" in README
    assert "**`space_bridge` ships off.**" in README


def test_confirm_numbers_in_readme_match_the_artifact() -> None:
    base, res = _art("passphrase_space_eff_confirm.json")["results"]
    p = lambda r, k: r["probe"][k]["total"]["leak_words"]
    sp = lambda r: r["probe"]["phrase"]["by_separator"]["space"]["leak_words"]
    assert f"| phrase probe leaked words | {p(base, 'phrase')} | **{p(res, 'phrase')}** (space-joined {sp(base)} → {sp(res)}) |" in README
    assert f"| connective probe leaked words (words on no list) | {p(base, 'connective')} | {p(res, 'connective')} |" in README
    assert f"| off-list phrase probe leaked words | {p(base, 'offlist_phrase')} | {p(res, 'offlist_phrase')} |" in README
    assert f"| SE test sentences flagged (all false positives) | {base['se']['sent_flagged']} / 306 | **{res['se']['sent_flagged']} / 306** (budget +1) |" in README


def test_calibration_numbers_in_readme_match_the_artifacts() -> None:
    v1 = _art("passphrase_space_calibration.json")["results"]
    assert [r["se"]["sent_flagged"] for r in v1] == [28, 56, 64, 75, 84]
    assert "28 flagged → 56 / 64 / 75 / 84; budget +5" in README
    e = _art("passphrase_space_eff_calibration.json")["results"]
    pick = next(r for r in e if r["arm"] == "func/2/eff3")
    assert (e[0]["probe"]["phrase"]["total"]["leak_words"], pick["probe"]["phrase"]["total"]["leak_words"]) == (454, 70)
    assert (e[0]["se"]["sent_flagged"], pick["se"]["sent_flagged"]) == (28, 30)
    assert "phrase leaks 454 → 70, SE train sentence flags 28 → 30" in README
