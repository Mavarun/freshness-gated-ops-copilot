"""The committed hazard-band artifact recomputes, and the one ANSWER on it leaks nothing."""

import importlib.util
import json
from pathlib import Path

from ops_copilot import hazard_band_protocol as P
from ops_copilot.pipeline import Copilot

ROOT = Path(__file__).resolve().parents[1]
ART = json.loads((ROOT / "artifacts" / "hazard_band.json").read_text())
spec = importlib.util.spec_from_file_location("hb", ROOT / "scripts" / "run_hazard_band_protocol.py")
S = importlib.util.module_from_spec(spec)
spec.loader.exec_module(S)


def test_rows_and_reading_recompute():
    rows = S.score()
    assert rows == ART["rows"]
    assert P.read(rows) == ART["read"]


def test_reading():
    r = ART["read"]
    assert r["holds"] and r["lost"] == []
    assert r["misfires"] == {"all": 6, "floor": 1, "off": 0} and r["correct"] == {"all": 12, "floor": 12, "off": 6}
    assert r["band_off_topic"] == ["hb-20"] and r["band_misfires"] == [] and r["guards_band"]
    assert r["answers"] == ["hb-05"]


def test_the_wrong_answer_cites_an_incident_thread_and_echoes_no_token():
    res = Copilot().ask(next(x["query"] for x in ART["rows"] if x["id"] == "hb-05"))
    assert res.decision.value == "ANSWER" and res.cited_ids == ["slack_inc_4821"]
    assert "xoxb-" not in (res.answer or "")
