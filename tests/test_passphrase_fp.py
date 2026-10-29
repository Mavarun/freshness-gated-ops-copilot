"""Committed false-positive check of the cued-passphrase detector on outside text."""

from __future__ import annotations

import json
from pathlib import Path

ART = Path(__file__).resolve().parents[1] / "artifacts" / "passphrase_fp_eval.json"


def test_false_positive_rate_on_stack_exchange_text_is_pinned() -> None:
    out = json.loads(ART.read_text())
    tr, te = out["train"], out["test"]
    assert tr["sentences"] > 2000 and te["sentences"] > 200
    assert tr["rate"] < 0.01 and te["rate"] < 0.01
    # 17 under the Oct 13 detector; 28 since the Oct 29 space-only incoherence arm (all 11 new
    # flags are space runs, within the pre-registered budget of 15)
    assert tr["flagged"] == 28 and te["flagged"] == 0
