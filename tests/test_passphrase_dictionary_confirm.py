"""The committed Oct 31 one-shot confirm: pick, every check, offline re-check of probe numbers."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from ops_copilot import passphrase_dictionary_protocol as P
from ops_copilot.passphrase_wordlist import score_rows

ART = Path(__file__).resolve().parents[1] / "artifacts" / "passphrase_dictionary_confirm.json"


@pytest.fixture(scope="module")
def conf() -> dict:
    return json.loads(ART.read_text())


def test_confirm_is_the_pre_registered_one_shot(conf: dict) -> None:
    assert conf["seeds"] == P.confirm_seeds() and conf["split"] == "test"
    assert conf["chosen"] == "ops/compounds/guard"
    assert [r["arm"] for r in conf["results"]] == ["ops/compounds/off", "ops/compounds/guard"]
    assert (conf["se_sentences"], conf["se_identifiers"]) == (306, 147)


def test_every_check_passes_and_it_ships(conf: dict) -> None:
    base, res = conf["results"]
    assert res["checks"] == P.confirm_passes(res, base)
    assert all(res["checks"].values()) and conf["ships"] is True


def test_headline_numbers(conf: dict) -> None:
    base, res = conf["results"]
    att = lambda r: (r["probe"]["attached"]["total"]["leak_rows"], r["probe"]["attached"]["total"]["leak_words"])
    assert att(base) == (456, 1948) and att(res) == (4, 10)
    assert base["probe"]["attached"]["total"]["words"] == 5890
    assert [r["probe"]["standard"]["total"]["leak_words"] for r in (base, res)] == [12, 12]
    assert [r["probe"]["invented"]["total"]["leak_words"] for r in (base, res)] == [0, 0]
    assert (res["se"]["ident_flagged"], res["se"]["ident_new"], res["se"]["sent_flagged"]) == (24, 0, 0)
    assert conf["offlist"]["ops/compounds/off"]["leak_words"] == conf["offlist"]["ops/compounds/guard"]["leak_words"] == 15


def test_probe_numbers_reproduce_offline(conf: dict) -> None:
    for arm, want in zip((P.SHIPPED, (("ops", "compounds"), "guard")), conf["results"]):
        pats = P.patterns_for(arm)
        got = {k: score_rows(P.probe_rows(k, s), pats)["total"] for k, s in P.confirm_seeds().items()}
        assert got == {k: want["probe"][k]["total"] for k in P.PROBES}
