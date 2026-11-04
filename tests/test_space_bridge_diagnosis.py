"""The committed post-hoc diagnosis of the Nov 4 space-bridge false flags (SE train only)."""

from __future__ import annotations

import json
from pathlib import Path

ART = Path(__file__).resolve().parents[1] / "artifacts" / "space_bridge_diagnosis.json"


def test_every_new_false_flag_has_an_off_list_word() -> None:
    d = json.loads(ART.read_text())
    assert d["sentences"] == 3025
    got = {a: (v["new_sentence_flags"], v["labels"]) for a, v in d["arms"].items()}
    assert got == {"prep/1": (28, {"not_all_eff": 28}), "prep/2": (36, {"not_all_eff": 36}),
                   "func/2": (47, {"not_all_eff": 47}), "stop/2": (56, {"not_all_eff": 56})}


def test_new_flags_match_the_calibration_artifact() -> None:
    cal = json.loads((ART.parent / "passphrase_space_calibration.json").read_text())
    d = json.loads(ART.read_text())
    base = cal["results"][0]["se"]["sent_flagged"]
    for r in cal["results"][1:]:
        assert r["se"]["sent_flagged"] - base == d["arms"][r["arm"]]["new_sentence_flags"]
