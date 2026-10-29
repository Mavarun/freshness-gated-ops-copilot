"""The committed one-shot confirm: ship rule and offline re-check of its probe numbers."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from ops_copilot import passphrase_tail_protocol as P
from ops_copilot.passphrase_wordlist import score_rows, wordlist_passphrases

ART = Path(__file__).resolve().parents[1] / "artifacts" / "passphrase_tail_confirm.json"


@pytest.fixture(scope="module")
def conf() -> dict:
    return json.loads(ART.read_text())


def test_confirm_is_the_pre_registered_run_and_ships_on(conf: dict) -> None:
    assert conf["seed"] == P.CONFIRM_SEED and conf["rows"] == P.N_ROWS
    assert conf["chosen"]["arm"] == "keep/0.10" and conf["shipped"]["arm"] == "trim/none"
    assert conf["se_test_candidates"] == 306
    assert all(conf["checks"].values()) and conf["ships_on"]
    assert (conf["shipped"]["probe"]["total"]["leak_words"], conf["chosen"]["probe"]["total"]["leak_words"]) == (93, 41)
    assert (conf["shipped"]["se"]["flagged"], conf["chosen"]["se"]["flagged"]) == (0, 0)


@pytest.mark.parametrize("key, arm", [("shipped", ("trim", None)), ("chosen", ("keep", 0.10))])
def test_confirm_probe_reproduces_offline(conf: dict, key: str, arm) -> None:
    rows = wordlist_passphrases(P.CONFIRM_SEED, P.N_ROWS)
    out = score_rows(rows, P.patterns_for(arm))
    assert out["total"] == conf[key]["probe"]["total"]
    assert out["cause"] == conf[key]["probe"]["cause"]
