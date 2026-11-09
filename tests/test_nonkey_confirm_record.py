"""The one-shot confirm record (spent 2026-11-09) and the ship call it implies."""

import json
from pathlib import Path

from ops_copilot import nonkey_coverage_protocol as P
from ops_copilot.config import CopilotConfig

ART = Path(__file__).resolve().parents[1] / "artifacts"


def _rec():
    return json.loads((ART / "nonkey_confirm.json").read_text(encoding="utf-8"))


def test_confirm_numbers():
    rec = _rec()
    a, s = rec["arms"]["all"], rec["arms"]["shipped"]
    assert (rec["arm"], rec["rows"], rec["swaps"]) == ("all", 301, 684)
    assert (s["passed"], a["passed"]) == (74, 32)
    assert (s["by_mechanism"]["unsupported"], a["by_mechanism"]["unsupported"]) == (29, 0)
    assert P.lost(a, s) == 3
    assert [r["id"] for r in rec["lost_rows"]] == ["d8-06", "d8-29", "d8-30"]
    assert rec["dev8_answered"] == {"shipped": 20, "all": 17}
    assert {k: len(v) for k, v in rec["topic_trap_opens"].items()} == {"shipped": 5, "all": 2}
    assert {k: len(v) for k, v in rec["attribute_trap_opens"].items()} == {"shipped": 0, "all": 0}


def test_ship_call_is_off_and_the_default_agrees():
    rec = _rec()
    a, s = rec["arms"]["all"], rec["arms"]["shipped"]
    call = P.ships(a, s, len(rec["attribute_trap_opens"]["all"]), len(rec["topic_trap_opens"]["all"]),
                   len(rec["topic_trap_opens"]["shipped"]))
    assert call is rec["ships"] is False  # 3 answered rows lost, budget 2
    assert CopilotConfig().grounding_nonkey_rule == "off"
