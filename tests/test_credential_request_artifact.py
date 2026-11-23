"""The committed credential-request artifact: its reading recomputes, and the fresh rows rescore."""

import importlib.util
import json
from pathlib import Path

from ops_copilot import credential_request_protocol as P

ROOT = Path(__file__).resolve().parents[1]
ART = json.loads((ROOT / "artifacts" / "credential_request.json").read_text())
spec = importlib.util.spec_from_file_location("cr", ROOT / "scripts" / "run_credential_request_protocol.py")
S = importlib.util.module_from_spec(spec)
spec.loader.exec_module(S)


def test_reading():
    assert ART["n_regression"] == 751 and ART["regression_changed_rows"] == []
    r = P.read([], ART["fresh"])
    for k in ("request_answered_off", "request_answered_on", "legit_changed", "legit_answered_off"):
        assert r[k] == ART["read"][k]
    a = ART["read"]
    assert a["request_answered_off"] == ["cr-05"] and a["request_answered_on"] == []
    assert a["legit_changed"] == [] and a["legit_answered_off"] == ["cr-18"] and a["ships"]


def test_fresh_rows_rescore():
    from dataclasses import replace

    from ops_copilot.config import CopilotConfig
    from ops_copilot.pipeline import Copilot
    off = Copilot(config=CopilotConfig(credential_request_gate=False))
    on = Copilot(config=replace(CopilotConfig(), credential_request_gate=True))
    for r in ART["fresh"]:
        assert off.ask(r["query"]).decision.value == r["off"], r["id"]
        assert on.ask(r["query"]).decision.value == r["on"], r["id"]


def test_shipped_default_is_the_on_arm():
    from ops_copilot.config import CopilotConfig
    assert CopilotConfig().credential_request_gate is True
