"""Post-hoc reading of the compound-parts calibration (selects nothing)."""

import json
from pathlib import Path

from ops_copilot.nonkey_parts_posthoc import same_source_doc
from ops_copilot.pipeline import Copilot

ART = Path(__file__).resolve().parents[1] / "artifacts"


def test_record_readings():
    rec = json.loads((ART / "nonkey_parts_posthoc.json").read_text(encoding="utf-8"))
    by = {r["id"]: r for r in rec["lost"]}
    assert list(by) == ["d5-22", "d6-06", "d8-30"]
    assert by["d6-06"]["reading"] == "wrong-evidence answer"
    assert by["d6-06"]["shipped_cited"] == ["rb_checkout_latency"]
    assert by["d6-06"]["source_cited"] == ["wiki_oncall_now"]
    assert by["d5-22"]["reading"] == "genuine loss" and by["d5-22"]["words"] == ["cadence"]
    assert by["d8-30"]["reading"] == "no source question" and by["d8-30"]["words"] == ["after"]


def test_shipped_default_answers_first_on_call_from_the_latency_runbook():
    # 'first' matches 'Do not bounce Redis as a first step'; the shipped default answers it
    bot = Copilot()
    res = bot.ask("Who is the first on-call right now?")
    assert res.decision.value == "ANSWER" and res.cited_ids == ["rb_checkout_latency"]
    assert same_source_doc(bot, "Who is the first on-call right now?", "Who is the primary on-call right now?") is False


def test_same_source_doc_accepts_extra_citations_and_skips_missing_sources():
    bot = Copilot()
    assert same_source_doc(bot, "What is the Vault AppRole rotation cadence?",
                           "What is the Vault AppRole rotation schedule?") is True
    assert same_source_doc(bot, "Who is the primary on-call right now?", None) is None
