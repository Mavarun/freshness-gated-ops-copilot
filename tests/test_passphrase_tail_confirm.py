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


AMENDED = Path(__file__).resolve().parents[1] / "artifacts" / "passphrase_tail_amended_confirm.json"


def test_first_confirm_ship_flag_is_superseded_by_the_amendment() -> None:
    from ops_copilot.passphrase import CUED_PASSPHRASE

    # keep/0.10 passed its own checks but is not the shipped arm (identifier flags)
    assert P.identifier_flags(("keep", 0.10)) != P.identifier_flags(P.SHIPPED)
    assert CUED_PASSPHRASE.coherence_compounds is False


def test_amended_confirm_ships_on_and_reproduces_offline() -> None:
    conf = json.loads(AMENDED.read_text())
    assert conf["seed"] == P.AMENDED_CONFIRM_SEED and conf["chosen"]["arm"] == "keep/0.10/space-only"
    assert all(conf["checks"].values()) and conf["ships_on"] and conf["new_identifier_flags"] == []
    rows = wordlist_passphrases(P.AMENDED_CONFIRM_SEED, P.N_ROWS)
    for key, arm in (("shipped", P.SHIPPED), ("chosen", P.AMENDED)):
        assert score_rows(rows, P.patterns_for(arm))["total"] == conf[key]["probe"]["total"]
    assert (conf["shipped"]["probe"]["total"]["leak_words"], conf["chosen"]["probe"]["total"]["leak_words"]) == (105, 76)


def test_shipped_patterns_are_the_amended_arm_plus_the_oct30_knobs() -> None:
    from ops_copilot import passphrase_compound_protocol as C
    from ops_copilot.explain_redact import SENSITIVE_PATTERNS

    rows = wordlist_passphrases(P.AMENDED_CONFIRM_SEED, 200)
    # the Oct 30 protocol's base arm is the amended Oct 29 arm, and the shipped set is its pick
    assert score_rows(rows, C.patterns_for(C.SHIPPED))["total"] == score_rows(rows, P.patterns_for(P.AMENDED))["total"]
    assert score_rows(rows, SENSITIVE_PATTERNS)["total"] == score_rows(rows, C.patterns_for(("all4", True, True)))["total"]
