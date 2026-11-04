"""The committed second Nov 4 calibration: func/2/eff3 is the pick and goes to the one-shot confirm."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from ops_copilot import passphrase_space_eff_protocol as E
from ops_copilot.passphrase_wordlist import score_rows

ART = Path(__file__).resolve().parents[1] / "artifacts" / "passphrase_space_eff_calibration.json"


@pytest.fixture(scope="module")
def cal() -> dict:
    return json.loads(ART.read_text())


def test_artifact_is_the_pre_registered_run(cal: dict) -> None:
    assert cal["seeds"] == E.CALIB_SEEDS and cal["rows"] == E.N_ROWS and cal["split"] == "train"
    assert [r["arm"] for r in cal["results"]] == [E.arm_name(a) for a in E.arms()]
    assert (cal["se_sentences"], cal["se_identifiers"]) == (3025, 1920)


def test_pick_rule_reproduces_the_choice(cal: dict) -> None:
    base, *rest = cal["results"]
    assert E.pick(rest, base)["arm"] == cal["pick"] == "func/2/eff3" and cal["passes"] is True
    assert all(all(E.calibration_passes(r, base).values()) for r in rest)


def test_numbers_the_readme_quotes(cal: dict) -> None:
    phrase = {r["arm"]: r["probe"]["phrase"]["total"]["leak_words"] for r in cal["results"]}
    assert phrase == {"shipped": 454, "prep/2/eff3": 160, "prep/2/eff4": 211, "func/2/eff3": 70, "func/2/eff4": 127}
    assert [r["se"]["sent_flagged"] for r in cal["results"]] == [28, 29, 29, 30, 29]


def test_controls_do_not_move(cal: dict) -> None:
    base, *rest = cal["results"]
    for k in ("connective", "offlist_phrase"):
        want = base["probe"][k]["total"]["leak_words"]
        assert all(r["probe"][k]["total"]["leak_words"] == want for r in rest)


@pytest.mark.parametrize("arm", [E.SHIPPED, ("func", 2, "eff3")])
def test_phrase_numbers_reproduce_offline(cal: dict, arm) -> None:
    got = score_rows(E.probe_rows("phrase", E.CALIB_SEEDS["phrase"]), E.patterns_for(arm))["total"]
    assert got == next(r for r in cal["results"] if r["arm"] == E.arm_name(arm))["probe"]["phrase"]["total"]
