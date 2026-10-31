"""The committed Oct 31 post-hoc artifact: the dictionary rule's leaks are compounds of invented words."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "artifacts" / "passphrase_dictionary_posthoc.json"


def test_leaks_split_by_shape_and_separator() -> None:
    out = json.loads(ART.read_text())
    for seed in ("3121", "3167"):
        c = out["invented"][seed]
        assert c["ops/compounds/off"]["cv"]["total"]["leak_words"] == c["ops/compounds/off"]["cvc"]["total"]["leak_words"] == 0
        assert c["dict_cv/compounds/guard"]["cv"]["total"]["leak_words"] == 0
        assert c["dict_cv/compounds/guard"]["cvc"]["total"]["leak_words"] == c["dict/compounds/guard"]["cvc"]["total"]["leak_words"] > 800
        assert c["dict/compounds/guard"]["cvc"]["by_separator"]["space"]["leak_rows"] == 0


def test_identifier_side() -> None:
    s = json.loads(ART.read_text())["se_train"]
    assert s["shipped_flags"] == 221
    assert (s["dict/compounds/guard"]["still_flagged"], s["dict/compounds/guard"]["dropped"]) == (48, 173)
    assert sum(s["dict/compounds/guard"]["dropped_by_shape"].values()) == 173


def test_invented_half_reproduces_offline() -> None:
    spec = importlib.util.spec_from_file_location("ph", ROOT / "scripts" / "run_passphrase_dictionary_posthoc.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    assert mod.run(None)["invented"] == json.loads(ART.read_text())["invented"]
