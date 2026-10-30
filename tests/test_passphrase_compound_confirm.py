"""The committed Oct 30 one-shot confirm: rule, numbers, offline re-check of the probe."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from ops_copilot import passphrase_compound_protocol as P
from ops_copilot.passphrase_wordlist import offlist_words, score_rows, wordlist_passphrases

ART = Path(__file__).resolve().parents[1] / "artifacts" / "passphrase_compound_confirm.json"


@pytest.fixture(scope="module")
def conf() -> dict:
    return json.loads(ART.read_text())


def test_confirm_is_the_pre_registered_one_shot(conf: dict) -> None:
    assert conf["seed"] == P.CONFIRM_SEED and conf["chosen"] == "all4/space/num"
    assert [r["arm"] for r in conf["results"]] == ["none/-/-", "all4/space/num"]
    assert (conf["se_sentences"], conf["se_identifiers"], conf["shipped_identifier_flags"]) == (306, 142, 23)
    base, res = conf["results"]
    assert P.confirm_passes(res, base) == res["confirm"] and all(res["confirm"].values()) and conf["ships"]


def test_confirm_numbers(conf: dict) -> None:
    base, res = conf["results"]
    assert (base["probe"]["total"]["leak_words"], res["probe"]["total"]["leak_words"]) == (128, 16)
    assert (base["probe"]["total"]["leak_rows"], res["probe"]["total"]["leak_rows"]) == (24, 4)
    assert (base["probe"]["total"]["over_words"], res["probe"]["total"]["over_words"]) == (507, 509)
    assert (base["se"]["flagged"], res["se"]["flagged"]) == (0, 0)
    assert res["idents"]["new_examples"] == ["client_header_buffer_size"]


def test_offlist_control_and_offline_reproduction(conf: dict) -> None:
    off = conf["offlist"]
    assert (off["none/-/-"]["leak_words"], off["all4/space/num"]["leak_words"]) == (63, 33)
    rows = wordlist_passphrases(P.CONFIRM_SEED, P.N_ROWS)
    for arm, r in zip((P.SHIPPED, ("all4", True, True)), conf["results"]):
        assert score_rows(rows, P.patterns_for(arm))["total"] == r["probe"]["total"]
    got = score_rows(wordlist_passphrases(P.OFFLIST_SEED, P.N_ROWS, words=offlist_words()), P.patterns_for(P.SHIPPED))
    assert got["total"] == off["none/-/-"]
