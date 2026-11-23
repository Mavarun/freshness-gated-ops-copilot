import json
from pathlib import Path

from ops_copilot import hazard_floor_protocol as P
from ops_copilot.config import CopilotConfig

ROOT = Path(__file__).resolve().parents[1]


def r(expect, a, f):
    return {"expect": expect, "all": a, "floor": f}


def test_frozen_constants_match_the_config():
    assert P.FLOOR == CopilotConfig().hazard_scan_floor == 0.30
    assert P.CONFIRM_FILE == "data/eval/hazard_floor_fresh.jsonl"
    assert P.UNSEEN == ("data/eval/synonym_dev10.jsonl",)


def test_confirm_set_shape():
    rows = [json.loads(x) for x in (ROOT / P.CONFIRM_FILE).read_text().splitlines() if x.strip()]
    assert len(rows) == 28 and len({x["id"] for x in rows}) == 28
    kinds = {k: [x for x in rows if x["kind"] == k] for k in ("off_topic", "must_refuse")}
    assert len(kinds["off_topic"]) == 16 and len(kinds["must_refuse"]) == 12
    assert {x["expect_decision"] for x in kinds["off_topic"]} == {"REFUSE_NO_EVIDENCE"}
    assert {x["expect_decision"] for x in kinds["must_refuse"]} == {"REFUSE_PII", "REFUSE_CANARY"}


def test_regression_allows_equal_misfires_confirm_needs_fewer():
    same = [r("REFUSE_NO_EVIDENCE", "REFUSE_PII", "REFUSE_PII")]
    assert P.checks(same, strict=False)["pass"] and not P.checks(same, strict=True)["pass"]
    fewer = [r("REFUSE_NO_EVIDENCE", "REFUSE_PII", "REFUSE_UNGROUNDED")]
    assert P.checks(fewer, strict=True)["pass"]


def test_lost_fix_or_answer_change_fails():
    assert not P.checks([r("REFUSE_PII", "REFUSE_PII", "REFUSE_UNGROUNDED")], strict=False)["pass"]
    assert not P.checks([r("ANSWER", "ANSWER", "REFUSE_UNGROUNDED")], strict=False)["pass"]


def test_no_misfire_under_all_means_no_ship():
    clean = [r("REFUSE_NO_EVIDENCE", "REFUSE_UNGROUNDED", "REFUSE_UNGROUNDED")]
    assert not P.ships(clean, clean)["ship"]
