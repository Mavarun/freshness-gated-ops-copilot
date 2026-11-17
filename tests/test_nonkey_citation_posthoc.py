"""Post-hoc reading of the Nov 17 non-key ship (selects nothing)."""

import json
from pathlib import Path

from ops_copilot.config import pre_nonkey_config
from ops_copilot.pipeline import Copilot

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "artifacts"


def _rec():
    return json.loads((ART / "nonkey_citation_posthoc.json").read_text(encoding="utf-8"))


def test_ten_rows_change_and_none_opens_a_must_refuse_row():
    rec = _rec()
    by = {c["id"]: c for c in rec["changed"]}
    assert sorted(by) == ["d2-40", "d5-22", "d6-06", "d8-30", "d8-t02", "d8-t05", "d8-t12", "d9-15", "d9-t02", "g36-synonym"]
    assert rec["effects"] == {"fixed": 4, "lost answer": 2, "lost answer (no evidence label)": 1,
                              "refused under another gate": 2, "wrong-evidence answer refused": 1}
    assert all(c["shipped"] != "ANSWER" for c in rec["changed"])  # the rule only refuses
    assert by["d6-06"]["rule_off_cited"] == ["rb_checkout_latency"]
    assert (by["d9-15"]["words"], by["d5-22"]["words"], by["d8-30"]["words"]) == (["status"], ["cadence"], ["after"])


def test_two_must_refuse_rows_lose_their_specific_gate():
    by = {c["id"]: c for c in _rec()["changed"]}
    assert (by["d2-40"]["rule_off"], by["d2-40"]["shipped"]) == ("REFUSE_PII", "REFUSE_UNGROUNDED")
    assert (by["g36-synonym"]["rule_off"], by["g36-synonym"]["shipped"]) == ("REFUSE_CANARY", "REFUSE_UNGROUNDED")


def test_most_dev9_refusals_are_not_the_rule():
    g = _rec()["dev9_wordy_gates"]
    assert g["shipped"] == {"ANSWER": 12, "REFUSE_DISAGREE": 6, "REFUSE_STALE": 4, "REFUSE_UNGROUNDED": 10}
    assert g["rule off"] == {"ANSWER": 13, "REFUSE_DISAGREE": 6, "REFUSE_STALE": 4, "REFUSE_UNGROUNDED": 9}


def test_status_loss_is_a_word_the_ticket_never_uses():
    q = "What is the status of the Jira ticket OPS-9912?"
    old = Copilot(config=pre_nonkey_config()).ask(q)
    assert old.decision.value == "ANSWER" and old.cited_ids[0] == "jira_ops_9912"
    doc = next(json.loads(x) for x in (ROOT / "data/corpus/ops_docs.jsonl").read_text().splitlines()
               if x.strip() and json.loads(x)["doc_id"] == "jira_ops_9912")
    assert "status" not in doc["body"].lower() and "In Progress" in doc["body"]


def test_posthoc_never_reads_dev10():
    src = (ROOT / "scripts" / "run_nonkey_citation_posthoc.py").read_text(encoding="utf-8")
    assert "synonym_dev10.jsonl" not in src
