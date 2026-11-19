"""Recompute of artifacts/hazard_scan.json (the 2026-11-20 protocol run)."""

from __future__ import annotations

import importlib.util
import json
from dataclasses import replace
from pathlib import Path

from ops_copilot import hazard_scan_protocol as P
from ops_copilot.config import CopilotConfig
from ops_copilot.pipeline import Copilot

ROOT = Path(__file__).resolve().parents[1]
ART = json.loads((ROOT / "artifacts/hazard_scan.json").read_text())


def _script():
    spec = importlib.util.spec_from_file_location("hz", ROOT / "scripts/run_hazard_scan_protocol.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_dev10_is_not_read() -> None:
    assert "dev10" not in json.dumps(ART)


def test_artifact_numbers() -> None:
    assert ART["n_rows"] == 751
    assert ART["effects"] == {"still wrong": 10, "fixed": 13}
    assert ART["checks"] == {"no_answer_change": True, "no_break": True, "fixes": True, "ship": True}
    fixed = sorted(c["id"] for c in ART["changed"] if c["effect"] == "fixed")
    assert "g36-synonym" in fixed and "d2-40" in fixed


def test_changed_rows_recompute() -> None:
    base = CopilotConfig()
    off = Copilot(config=replace(base, hazard_scan_on_ungrounded=False))
    on = Copilot(config=replace(base, hazard_scan_on_ungrounded=True))
    rows = {r["id"]: r for r in _script().rows()}
    sub = [rows[c["id"]] for c in ART["changed"]]
    got = _script().score(off, on, sub)
    assert got["changed"] == ART["changed"]
