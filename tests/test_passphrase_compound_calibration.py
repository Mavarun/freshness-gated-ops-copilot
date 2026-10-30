"""The committed Oct 30 calibration artifact: pick, budgets, offline re-check of probe numbers."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from ops_copilot import passphrase_compound_protocol as P
from ops_copilot.passphrase_wordlist import score_rows, wordlist_passphrases

ART = Path(__file__).resolve().parents[1] / "artifacts" / "passphrase_compound_calibration.json"


@pytest.fixture(scope="module")
def cal() -> dict:
    return json.loads(ART.read_text())


def test_artifact_is_the_pre_registered_run(cal: dict) -> None:
    assert cal["seed"] == P.CALIB_SEED and cal["rows"] == P.N_ROWS
    assert [r["arm"] for r in cal["results"]] == [P.arm_name(a) for a in P.arms()]
    assert (cal["se_sentences"], cal["se_identifiers"], cal["shipped_identifier_flags"]) == (3020, 1867, 221)
    assert cal["chosen"] == "all4/space/num"


def test_pick_rule_and_which_arms_fail(cal: dict) -> None:
    base = cal["results"][0]
    assert P.pick(cal["results"], base)["arm"] == cal["chosen"]
    unsafe = {r["arm"]: [k for k, v in r["safe"].items() if not v] for r in cal["results"] if not all(r["safe"].values())}
    assert set(unsafe) == {P.arm_name(a) for a in P.arms() if a[0] in ("but1_4", "all3")}
    assert all(v == ["ident_budget"] for v in unsafe.values())
    new = {r["arm"].split("/")[0]: r["idents"]["new_flags"] for r in cal["results"]}
    assert (new["all4"], new["but1_4"], new["all3"]) == (0, 16, 28)


def test_headline_numbers(cal: dict) -> None:
    by = {r["arm"]: r["probe"]["total"] for r in cal["results"]}
    assert (by["none/-/-"]["leak_words"], by["none/-/num"]["leak_words"], by["all4/-/-"]["leak_words"],
            by["all4/space/num"]["leak_words"]) == (136, 77, 100, 37)
    assert (by["none/-/-"]["over_words"], by["all4/space/num"]["over_words"]) == (533, 535)
    assert {r["se"]["flagged"] for r in cal["results"]} == {28}


@pytest.mark.parametrize("arm", [P.SHIPPED, ("all4", True, True)])
def test_probe_numbers_reproduce_offline(cal: dict, arm) -> None:
    got = score_rows(wordlist_passphrases(P.CALIB_SEED, P.N_ROWS), P.patterns_for(arm))["total"]
    assert got == next(r for r in cal["results"] if r["arm"] == P.arm_name(arm))["probe"]["total"]
