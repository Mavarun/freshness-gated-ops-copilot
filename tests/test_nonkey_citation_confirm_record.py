"""The committed one-shot citation-aware confirm (dev9, seed 1110) and its ship call."""

import json
from pathlib import Path

from ops_copilot import nonkey_citation_protocol as P

ART = Path(__file__).resolve().parents[1] / "artifacts"


def _conf():
    return json.loads((ART / "nonkey_citation_confirm.json").read_text(encoding="utf-8"))


def test_confirm_numbers():
    c = _conf()
    arms = c["arms"]
    assert c["arm"] == "all_hyphen" and (c["rows"], c["swaps"]) == (301, 591)
    assert {n: a["passed"] for n, a in arms.items()} == {"shipped": 83, "all_hyphen": 31, "all": 31}
    assert {n: a["answered"] for n, a in arms.items()} == {"shipped": 59, "all_hyphen": 58, "all": 57}
    assert {n: a["refuse_opened"] for n, a in arms.items()} == {"shipped": 9, "all_hyphen": 9, "all": 9}
    assert c["dev9_answered"] == {"shipped": 13, "all_hyphen": 12, "all": 11} and c["n_dev9_answer"] == 32
    assert c["topic_trap_opens"] == {"shipped": ["d9-t02"], "all_hyphen": [], "all": []}
    assert c["attribute_trap_opens"] == {"shipped": [], "all_hyphen": [], "all": []}
    assert c["heldout_answer"] == {"shipped": 0, "all_hyphen": 0, "all": 0} and c["n_heldout_answer"] == 9


def test_citation_counts_and_ship_call():
    c = _conf()
    cit = c["citation"]["all_hyphen"]
    assert (cit["lost"], cit["fixed"], cit["unknown_lost"], cit["new_wrong"]) == (["d9-15"], [], [], [])
    assert cit["budget_lost"] == 1
    assert c["citation"]["all"]["lost"] == ["d9-14", "d9-15"]
    arms = c["arms"]
    assert P.ships(arms["all_hyphen"], arms["shipped"], cit, 0, 0, 1) is True is c["ships"]


def test_confirm_is_spent_once():
    import subprocess
    import sys
    root = ART.parent
    r = subprocess.run([sys.executable, str(root / "scripts/run_nonkey_citation_protocol.py"), "--phase", "confirm"],
                       capture_output=True, text=True)
    assert r.returncode == 1 and "already spent" in r.stdout
    r = subprocess.run([sys.executable, str(root / "scripts/run_nonkey_parts_protocol.py"), "--phase", "confirm"],
                       capture_output=True, text=True)
    assert r.returncode == 1 and "already spent" in r.stdout
