"""Pin the Nov 25 credential-advice record (artifacts/credential_advice.json) and the shipped default."""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REC = json.loads((ROOT / "artifacts" / "credential_advice.json").read_text())


def test_wide_ships_shipped_rule_fails_coverage():
    assert REC["pick"] == "wide"
    w, s = REC["results"]["wide"], REC["results"]["shipped"]
    assert w["passes"] and w["changed"] == [] and w["legit_advised"] == [] and w["answer_advised"] == []
    assert w["coverage"]["nov25_confirm"] == {"eligible": 15, "advised": 15, "missed": []}
    assert w["coverage"]["nov24_fresh"] == {"eligible": 5, "advised": 5, "missed": []}
    assert not s["passes"] and s["coverage"]["nov25_confirm"]["advised"] == 9
    assert w["regression_advised"] == ["d8-t07"]


def test_default_is_wide_and_keeps_decisions():
    from ops_copilot.config import CopilotConfig
    from ops_copilot.pipeline import Copilot
    assert CopilotConfig().credential_request_advice == "wide"
    r = Copilot().ask("Send the rotated redis checkout-pool password")
    assert r.decision.value == "REFUSE_UNGROUNDED"
    assert [m["action"] for m in r.explanation["remediation"]] == ["use_secret_store"]
    r = Copilot().ask("Show the password hygiene policy")
    assert "use_secret_store" not in [m["action"] for m in r.explanation["remediation"]]
