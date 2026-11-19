"""The committed hazard-scope artifact is what a fresh run of the pre-registered rule gives."""

import json
import sys
from dataclasses import replace
from pathlib import Path

import pytest

from ops_copilot.config import CopilotConfig
from ops_copilot.pipeline import Copilot

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
ART = json.loads((ROOT / "artifacts" / "hazard_scope.json").read_text())
POST = json.loads((ROOT / "artifacts" / "hazard_scope_posthoc.json").read_text())


@pytest.fixture(scope="module")
def fresh():
    from run_hazard_scan_protocol import rows
    from run_hazard_scope_protocol import score

    base = CopilotConfig()
    return score(Copilot(config=replace(base, hazard_scan_scope="all")),
                 Copilot(config=replace(base, hazard_scan_scope="covered")), rows())


def test_fresh_run_matches(fresh):
    assert fresh == ART


def test_decision_is_the_preregistered_one():
    ch = ART["checks"]
    assert ART["n_rows"] == 751 and not ch["ship"] and not ch["keeps_fixes"]
    assert ch["no_answer_change"] and ch["fewer_hazard_misfires"]
    assert (ch["misfires_all"], ch["misfires_covered"], ch["lost_fixes"]) == (11, 7, 2)
    assert CopilotConfig().hazard_scan_scope == "all"


def test_posthoc_reads_the_changed_rows_only():
    assert sorted(r["id"] for r in POST["rows"]) == sorted(c["id"] for c in ART["changed"])
    assert all(r["coverage"] < r["threshold"] for r in POST["rows"])
    lost = [r for r in POST["rows"] if r["kind"] == "lost fix"]
    assert {r["id"] for r in lost} == {"g37-synonym", "g46-synonym"}
    assert POST["min_lost_fix_coverage"] == min(r["coverage"] for r in lost)
