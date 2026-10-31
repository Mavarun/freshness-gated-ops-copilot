"""The committed Oct 31 calibration artifact: pick, which checks fail, offline re-check of probe numbers."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from ops_copilot import passphrase_dictionary_protocol as P
from ops_copilot.passphrase_wordlist import score_rows

ART = Path(__file__).resolve().parents[1] / "artifacts" / "passphrase_dictionary_calibration.json"


@pytest.fixture(scope="module")
def cal() -> dict:
    return json.loads(ART.read_text())


def test_artifact_is_the_pre_registered_run(cal: dict) -> None:
    assert cal["seeds"] == P.calib_seeds() and cal["split"] == "train" and cal["rows"] == P.N_ROWS
    assert [r["arm"] for r in cal["results"]] == [P.arm_name(a) for a in P.arms()]
    assert (cal["se_sentences"], cal["se_identifiers"]) == (3025, 1920)
    assert cal["chosen"] == "ops/compounds/guard"


def test_pick_and_failures(cal: dict) -> None:
    base = cal["results"][0]
    assert P.pick(cal["results"], base)["arm"] == cal["chosen"]
    unsafe = {r["arm"]: [k for k, v in r["safe"].items() if not v] for r in cal["results"] if not all(r["safe"].values())}
    assert unsafe.pop("ops/compounds/raw") == ["se_identifiers"]
    assert set(unsafe) == {P.arm_name(a) for a in P.arms() if a[0][0] != "ops"}
    assert all(v == ["invented_budget"] for v in unsafe.values())


def test_headline_numbers(cal: dict) -> None:
    by = {r["arm"]: r for r in cal["results"]}
    lw = lambda a, k: by[a]["probe"][k]["total"]["leak_words"]
    assert (lw("ops/compounds/off", "attached"), lw("ops/compounds/guard", "attached")) == (2081, 16)
    assert (lw("dict/compounds/off", "invented"), lw("dict_cv/compounds/off", "invented")) == (1294, 888)
    ids = {a: by[a]["se"]["ident_flagged"] for a in ("ops/compounds/off", "dict/compounds/off", "dict_cv/compounds/off")}
    assert ids == {"ops/compounds/off": 221, "dict/compounds/off": 48, "dict_cv/compounds/off": 53}
    assert by["ops/compounds/raw"]["se"]["ident_new"] == 12 and by["ops/compounds/guard"]["se"]["ident_new"] == 0


def test_probe_numbers_reproduce_offline(cal: dict) -> None:
    for arm in (P.SHIPPED, (("ops", "compounds"), "guard")):
        pats = P.patterns_for(arm)
        got = {k: score_rows(P.probe_rows(k, s), pats)["total"] for k, s in P.calib_seeds().items()}
        want = next(r for r in cal["results"] if r["arm"] == P.arm_name(arm))["probe"]
        assert got == {k: want[k]["total"] for k in P.PROBES}
