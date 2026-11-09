import json
from pathlib import Path

from ops_copilot.nonkey_posthoc import hyphen_parts

ART = Path(__file__).resolve().parents[1] / "artifacts"


def test_hyphen_parts_split_compounds_and_skip_digit_tokens():
    parts = hyphen_parts("Primary on-call right now is Asha Patel (pager checkout-primary). us-east-1 only.")
    assert {"checkout", "primary", "on", "call"} <= parts
    assert "east" not in parts  # tokens with digits are identifiers, never split
    assert hyphen_parts("no compounds here") == set()


def test_posthoc_record():
    rec = json.loads((ART / "nonkey_posthoc.json").read_text(encoding="utf-8"))
    assert [r["id"] for r in rec["lost"]] == ["d5-22", "d6-06", "d8-06", "d8-29", "d8-30"]
    assert rec["lost_compound_part"] == 2
    kinds = {t["id"]: (t["kind"], t["arm_decision"]) for t in rec["traps"]}
    assert kinds == {
        "d8-t02": ("non-key unsupported", "REFUSE_UNGROUNDED"),
        "d8-t03": ("lexical", "ANSWER"),
        "d8-t05": ("non-key unsupported", "REFUSE_UNGROUNDED"),
        "d8-t08": ("lexical", "ANSWER"),
        "d8-t12": ("non-key unsupported", "REFUSE_UNGROUNDED"),
    }
