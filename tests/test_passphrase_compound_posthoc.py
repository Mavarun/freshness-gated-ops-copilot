"""Oct 30 post-hoc artifact: knob attribution, remaining leaks, Bitwarden-style numbers."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from ops_copilot.passphrase_wordlist import eff_words, wordlist_passphrases

ART = Path(__file__).resolve().parents[1] / "artifacts" / "passphrase_compound_posthoc.json"


def test_attached_style_rows() -> None:
    rows = wordlist_passphrases(11, 40, number_style="attached")
    assert rows == wordlist_passphrases(11, 40, number_style="attached")
    assert all(sum(c.isdigit() for c in r.secret) == 1 and set(r.words) <= set(eff_words()) for r in rows)
    with pytest.raises(ValueError):
        wordlist_passphrases(11, 4, number_style="prefix")


def test_attribution_and_gap_numbers() -> None:
    out = json.loads(ART.read_text())
    a = {k: (v["confirm"]["leak_words"], v["offlist"]["leak_words"]) for k, v in out["attribution"].items()}
    assert a["none/-/-"] == (128, 63) and a["none/-/num"] == (39, 33) and a["all4/-/-"] == (109, 63)
    assert a["all4/space/num"] == (16, 33)
    # the list arms add nothing on the off-list control; the purpose fix does all of it there
    assert {v[1] for k, v in a.items() if k.endswith("/num")} == {33}
    assert len(out["confirm_leaks"]) == 4
    att = out["attached"]
    assert att["oct29"]["total"] == att["shipped"]["total"]
    assert (att["shipped"]["total"]["leak_rows"], att["shipped"]["total"]["leak_words"]) == (452, 1977)
