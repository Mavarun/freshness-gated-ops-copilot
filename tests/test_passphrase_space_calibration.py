"""The committed Nov 4 space-bridge calibration: no arm is safe, so the confirm seeds stay unspent."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from ops_copilot import passphrase_space_protocol as F
from ops_copilot.passphrase_wordlist import score_rows

ART = Path(__file__).resolve().parents[1] / "artifacts"


@pytest.fixture(scope="module")
def cal() -> dict:
    return json.loads((ART / "passphrase_space_calibration.json").read_text())


def test_artifact_is_the_pre_registered_run(cal: dict) -> None:
    assert cal["seeds"] == F.CALIB_SEEDS and cal["rows"] == F.N_ROWS and cal["split"] == "train"
    assert [r["arm"] for r in cal["results"]] == [F.arm_name(a) for a in F.arms()]
    assert (cal["se_sentences"], cal["se_identifiers"]) == (3025, 1920)


def test_no_arm_is_safe_because_of_se_sentence_flags(cal: dict) -> None:
    base, *rest = cal["results"]
    assert base["se"]["sent_flagged"] == 28
    for r in rest:
        chk = F.calibration_passes(r, base)
        assert not chk.pop("se_sentences") and all(chk.values()), r["arm"]
        assert r["se"]["sent_flagged"] - 28 > F.SENT_BUDGET_TRAIN
    assert F.pick(rest, base) is None and cal["pick"] is None and cal["passes"] is False


def test_the_gain_is_real_but_not_free(cal: dict) -> None:
    base, *rest = cal["results"]
    phrase = {r["arm"]: r["probe"]["phrase"]["total"]["leak_words"] for r in cal["results"]}
    assert phrase == {"shipped": 468, "prep/1": 207, "prep/2": 207, "func/2": 94, "stop/2": 94}
    assert [r["se"]["sent_flagged"] for r in rest] == [56, 64, 75, 84]
    assert all(r["probe"]["connective"]["total"]["leak_words"] <= base["probe"]["connective"]["total"]["leak_words"] for r in rest)


@pytest.mark.parametrize("arm", [F.SHIPPED, ("func", 2)])
def test_probe_numbers_reproduce_offline(cal: dict, arm) -> None:
    rows = F.probe_rows("phrase", F.CALIB_SEEDS["phrase"])
    got = score_rows(rows, F.patterns_for(arm))["total"]
    assert got == next(r for r in cal["results"] if r["arm"] == F.arm_name(arm))["probe"]["phrase"]["total"]
