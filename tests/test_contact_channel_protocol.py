import json
from pathlib import Path

from ops_copilot import contact_channel_protocol as P

ROOT = Path(__file__).resolve().parents[1]


def _r(expect, phrases, channel):
    return {"expect": expect, "phrases": phrases, "channel": channel}


def test_confirm_set_shape_and_unseen_dev10() -> None:
    rows = [json.loads(x) for x in (ROOT / P.CONFIRM_FILE).read_text().splitlines() if x.strip()]
    assert len(rows) == 19 and len({r["id"] for r in rows}) == 19
    assert sum(r["expect_decision"] == "ANSWER" for r in rows) == 11
    assert sum(r["expect_decision"] == "REFUSE_PII" for r in rows) == 8
    assert P.CONFIRM_FILE not in P.EVAL_FILES and "data/eval/synonym_dev10.jsonl" in P.UNSEEN


def test_misfire_definition() -> None:
    assert P.is_misfire("ANSWER", "REFUSE_PII")
    assert P.is_misfire("REFUSE_NO_EVIDENCE", "REFUSE_CANARY")
    assert not P.is_misfire("REFUSE_PII", "REFUSE_CANARY")
    assert not P.is_misfire("ANSWER", "REFUSE_UNGROUNDED")


def test_ships_when_all_hold() -> None:
    a = [_r("ANSWER", "REFUSE_PII", "ANSWER"), _r("ANSWER", "REFUSE_PII", "REFUSE_UNGROUNDED")]
    b = [_r("ANSWER", "REFUSE_PII", "ANSWER"), _r("REFUSE_PII", "REFUSE_PII", "REFUSE_PII")]
    assert P.checks(a, b)["ship"]


def test_each_check_can_fail() -> None:
    ok_b = [_r("REFUSE_PII", "REFUSE_PII", "REFUSE_PII")]
    mis = _r("ANSWER", "REFUSE_PII", "REFUSE_UNGROUNDED")
    assert not P.checks([mis, _r("REFUSE_PII", "REFUSE_PII", "ANSWER")], ok_b)["no_trap_opened"]
    assert not P.checks([mis, _r("REFUSE_PII", "REFUSE_PII", "REFUSE_UNGROUNDED")], ok_b)["no_break"]
    assert not P.checks([_r("ANSWER", "REFUSE_UNGROUNDED", "REFUSE_UNGROUNDED")], ok_b)["fewer_misfires"]
    assert not P.checks([mis], [_r("REFUSE_PII", "REFUSE_PII", "ANSWER")])["fresh_no_trap"]
    assert not P.checks([mis], [_r("ANSWER", "ANSWER", "REFUSE_PII")])["fresh_no_worse"]
