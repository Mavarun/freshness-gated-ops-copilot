"""The committed one-shot confirm of the list-only space bridge: the gain holds, the SE test budget does not."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from ops_copilot import passphrase_space_eff_protocol as E
from ops_copilot.passphrase import CUED_PASSPHRASE
from ops_copilot.passphrase_wordlist import score_rows

ART = Path(__file__).resolve().parents[1] / "artifacts"


@pytest.fixture(scope="module")
def conf() -> dict:
    return json.loads((ART / "passphrase_space_eff_confirm.json").read_text())


def test_confirm_is_the_one_shot_on_the_calibration_pick(conf: dict) -> None:
    cal = json.loads((ART / "passphrase_space_eff_calibration.json").read_text())
    assert conf["seeds"] == E.CONFIRM_SEEDS and conf["split"] == "test" and conf["pick"] == cal["pick"] == "func/2/eff3"
    assert [r["arm"] for r in conf["results"]] == ["shipped", "func/2/eff3"]
    assert (conf["se_sentences"], conf["se_identifiers"]) == (306, 147)


def test_the_only_failed_check_is_se_sentences_so_the_knob_ships_off(conf: dict) -> None:
    base, res = conf["results"]
    chk = E.confirm_passes(res, base)
    assert [k for k, v in chk.items() if not v] == ["se_sentences"] and conf["passes"] is False
    assert (base["se"]["sent_flagged"], res["se"]["sent_flagged"]) == (0, 2)
    assert CUED_PASSPHRASE.space_bridge is None and CUED_PASSPHRASE.space_bridge_rule == "plain"


def test_phrase_gain_and_controls(conf: dict) -> None:
    base, res = conf["results"]
    leak = lambda r, k: r["probe"][k]["total"]["leak_words"]
    assert (leak(base, "phrase"), leak(res, "phrase")) == (420, 49)
    assert (leak(base, "phrase") - leak(res, "phrase")) == base["probe"]["phrase"]["by_separator"]["space"]["leak_words"] - res["probe"]["phrase"]["by_separator"]["space"]["leak_words"]
    for k in ("connective", "offlist_phrase", "standard", "attached", "invented", "cased"):
        assert leak(res, k) == leak(base, k)
    assert (leak(base, "offlist_phrase"), leak(base, "connective")) == (457, 173)


def test_phrase_numbers_reproduce_offline(conf: dict) -> None:
    got = score_rows(E.probe_rows("phrase", E.CONFIRM_SEEDS["phrase"]), E.patterns_for(("func", 2, "eff3")))["total"]
    assert got == conf["results"][1]["probe"]["phrase"]["total"]
