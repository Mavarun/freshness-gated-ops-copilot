"""Unit-test literal sweep: the dev3-chosen Datamuse arm opens a labelled trap, so it ships off."""

import json
from pathlib import Path

from ops_copilot.config import CopilotConfig
from ops_copilot.datamuse_dev3 import config_for
from ops_copilot.safety_sweep import LABELLED, sweep, test_literal_queries

ROOT = Path(__file__).resolve().parents[1]
REVERT = "What is the revert procedure for the checkout_retry feature toggle?"


def test_collects_query_literals_including_every_labelled_one():
    qs = test_literal_queries()
    assert len(qs) >= 100
    assert set(LABELLED) <= set(qs)
    for q, (_label, where) in LABELLED.items():
        assert q in (ROOT / where.split("::")[0]).read_text(encoding="utf-8")


def test_chosen_arm_opens_the_revert_toggle_trap_and_default_does_not():
    chosen = json.loads((ROOT / "artifacts" / "datamuse_dev3_confirm.json").read_text())["chosen"]
    rep = sweep(config_for(chosen), queries=[REVERT, "What is the chargeback runbook for INC-4821?"])
    assert [c["query"] for c in rep["changed"]] == [REVERT]
    assert rep["changed"][0]["base"] == "REFUSE_UNGROUNDED" and rep["changed"][0]["candidate"] == "ANSWER"
    assert rep["safe"] is False
    same = sweep(CopilotConfig(), queries=[REVERT])
    assert same["changed"] == [] and same["safe"] is True


def test_committed_sweep_artifact_and_the_shipped_flag():
    rep = json.loads((ROOT / "artifacts" / "datamuse_dev3_safety_sweep.json").read_text())
    assert rep["safe"] is False and rep["ships"].startswith("off")
    assert [c["query"] for c in rep["labelled_trap_opened"]] == [REVERT]
    # the confirm rule alone said on; the sweep overrides it and the default stays off
    assert json.loads((ROOT / "artifacts" / "datamuse_dev3_confirm.json").read_text())["decision"]["default_on"]
    assert CopilotConfig().use_datamuse_ml is False and CopilotConfig().datamuse_context_min == 0
