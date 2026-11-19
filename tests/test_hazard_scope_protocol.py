"""The pre-registered hazard_scan_scope rule, on hand-made rows."""

from ops_copilot import hazard_scope_protocol as P


def _r(expect, a, c):
    return {"expect": expect, "all": a, "covered": c}


def test_ships_when_a_misfire_goes_and_nothing_else_moves():
    rows = [_r("REFUSE_NO_EVIDENCE", "REFUSE_PII", "REFUSE_UNGROUNDED"), _r("REFUSE_PII", "REFUSE_PII", "REFUSE_PII"),
            _r("ANSWER", "ANSWER", "ANSWER")]
    out = P.ships(rows)
    assert out["ship"] and out["misfires_all"] == 1 and out["misfires_covered"] == 0


def test_each_check_can_fail():
    assert not P.ships([_r("REFUSE_CANARY", "REFUSE_CANARY", "REFUSE_UNGROUNDED"),
                        _r("ANSWER", "REFUSE_PII", "REFUSE_UNGROUNDED")])["keeps_fixes"]
    assert not P.ships([_r("ANSWER", "ANSWER", "REFUSE_UNGROUNDED"),
                        _r("ANSWER", "REFUSE_PII", "REFUSE_UNGROUNDED")])["no_answer_change"]
    assert not P.ships([_r("ANSWER", "REFUSE_PII", "REFUSE_PII")])["fewer_hazard_misfires"]


def test_row_files_match_the_morning_protocol_and_skip_dev10():
    from ops_copilot import hazard_scan_protocol as H

    assert P.EVAL_FILES == H.EVAL_FILES and "data/eval/synonym_dev10.jsonl" not in P.EVAL_FILES
