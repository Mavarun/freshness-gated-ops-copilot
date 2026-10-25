"""Post-hoc null-control diagnosis artifact: pinned numbers quoted in the README."""

import json
from pathlib import Path

from ops_copilot.attribute_traps import half as trap_half
from ops_copilot.synonym_dev5 import half

ART = Path(__file__).resolve().parents[1] / "artifacts" / "passage_null_diagnosis.json"


def test_diagnosis_numbers():
    rep = json.loads(ART.read_text())
    assert rep["post_hoc"] is True and rep["n_controls"] == 100
    assert (rep["n_keep"], rep["n_trap"]) == (43, 6)
    assert rep["trap_margin_max"] < 0
    assert rep["keep_at_or_below_trap_max"] == ["d3-27", "d4-29"]
    assert rep["keep_answer_at_or_below_trap_max"] == []
    assert sorted(rep["open_at_q050_per_call"]) == ["at-22", "at-25"]
    assert rep["open_at_q050_per_call"]["at-25"]["call_percentiles"][0] < 0.5


def test_diagnosis_never_reads_confirm_rows():
    rep = json.loads(ART.read_text())
    confirm = {r["id"] for r in half("confirm")} | {r["id"] for r in trap_half("confirm")}
    assert not confirm & {x["id"] for x in rep["rows"]}
