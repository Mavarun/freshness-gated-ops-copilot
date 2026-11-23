import json
from pathlib import Path

from ops_copilot import hazard_band_protocol as P

ROOT = Path(__file__).resolve().parents[1]
ROWS = [json.loads(x) for x in (ROOT / P.BAND_FILE).read_text().splitlines() if x.strip()]


def test_fresh_set_shape_and_labels():
    assert len(ROWS) == 24 and len({r["id"] for r in ROWS}) == 24
    kinds = [r["kind"] for r in ROWS]
    assert kinds.count("must_refuse") == 12 and kinds.count("off_topic") == 12
    labels = [r["expect_decision"] for r in ROWS]
    assert labels.count("REFUSE_PII") == 6 and labels.count("REFUSE_CANARY") == 6
    assert all(r["expect_decision"] == "REFUSE_NO_EVIDENCE" for r in ROWS if r["kind"] == "off_topic")


def test_no_overlap_with_earlier_eval_sets():
    seen = set()
    for f in (ROOT / "data" / "eval").glob("*.jsonl"):
        if f.name != Path(P.BAND_FILE).name:
            seen |= {json.loads(x).get("query", "").lower() for x in f.read_text().splitlines() if x.strip()}
    assert not seen & {r["query"].lower() for r in ROWS}


def _row(i, kind, expect, cov, a, f, o):
    return {"id": i, "kind": kind, "expect": expect, "coverage": cov, "all": a, "floor": f, "off": o}


def test_reading_on_hand_made_rows():
    rows = [_row("m1", "must_refuse", "REFUSE_PII", 0.6, "REFUSE_PII", "REFUSE_PII", "REFUSE_UNGROUNDED"),
            _row("m2", "must_refuse", "REFUSE_PII", 0.2, "REFUSE_PII", "REFUSE_UNGROUNDED", "REFUSE_UNGROUNDED"),
            _row("o1", "off_topic", "REFUSE_NO_EVIDENCE", 0.35, "REFUSE_PII", "REFUSE_PII", "REFUSE_UNGROUNDED"),
            _row("o2", "off_topic", "REFUSE_NO_EVIDENCE", 0.40, "REFUSE_UNGROUNDED", "REFUSE_UNGROUNDED", "REFUSE_UNGROUNDED"),
            _row("o3", "off_topic", "REFUSE_NO_EVIDENCE", 0.20, "REFUSE_PII", "REFUSE_UNGROUNDED", "REFUSE_UNGROUNDED")]
    r = P.read(rows)
    assert r["lost"] == ["m2"] and not r["holds"]
    assert r["band_off_topic"] == ["o1", "o2"] and r["band_misfires"] == ["o1"] and r["band_misfire_share"] == 0.5
    assert not r["guards_band"] and r["answers"] == []
    assert r["misfires"] == {"all": 2, "floor": 1, "off": 0}
