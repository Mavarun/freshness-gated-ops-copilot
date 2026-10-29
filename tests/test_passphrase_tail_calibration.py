"""The committed Oct 29 calibration artifact: pick, and offline re-check of its probe numbers."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from ops_copilot import passphrase_tail_protocol as P
from ops_copilot.passphrase_wordlist import score_rows, wordlist_passphrases

ART = Path(__file__).resolve().parents[1] / "artifacts" / "passphrase_tail_calibration.json"


@pytest.fixture(scope="module")
def cal() -> dict:
    return json.loads(ART.read_text())


def test_artifact_is_the_pre_registered_run(cal: dict) -> None:
    assert cal["seed"] == P.CALIB_SEED and cal["rows"] == P.N_ROWS
    assert [r["arm"] for r in cal["results"]] == [P.arm_name(a) for a in P.arms()]
    assert cal["se_train_candidates"] == 3020
    assert cal["chosen"] == "keep/0.10"


def test_pick_rule_reproduces_the_choice(cal: dict) -> None:
    base = cal["results"][0]
    assert P.pick(cal["results"], base)["arm"] == cal["chosen"]
    unsafe = {r["arm"] for r in cal["results"] if not all(r["safe"].values())}
    assert unsafe == {"trim/0.12", "trim/0.15", "keep/0.12", "keep/0.15"}
    assert all(not r["safe"]["fp_budget"] for r in cal["results"] if r["arm"] in unsafe)


@pytest.mark.parametrize("arm", [("trim", None), ("keep", 0.10)])
def test_probe_numbers_reproduce_offline(cal: dict, arm) -> None:
    rows = wordlist_passphrases(P.CALIB_SEED, P.N_ROWS)
    got = score_rows(rows, P.patterns_for(arm))["total"]
    want = next(r for r in cal["results"] if r["arm"] == P.arm_name(arm))["probe"]["total"]
    assert got == want
