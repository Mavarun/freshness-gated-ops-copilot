import json
from pathlib import Path

from ops_copilot.resource_agreement import SOURCES, AgreementSense
from ops_copilot.resource_agreement_posthoc import pair_coverage, single_word_pairs

ART = Path(__file__).resolve().parents[1] / "artifacts"


def _post():
    return json.loads((ART / "resource_agreement_posthoc.json").read_text(encoding="utf-8"))


def test_single_word_pairs_drop_phrases():
    assert single_word_pairs(["a->b", "error budget->slo headroom", "x->Y"]) == [("a", "b"), ("x", "y")]


def test_pair_coverage_counts_gold_votes():
    table = {"wordvec": {"usage": {"utilization"}}, "datamuse": {"usage": {"utilization"}}, "wordnet": {"usage": {"use"}}}
    prop = {n: (lambda t, n=n: frozenset(table.get(n, {}).get(t, ()))) for n in SOURCES}
    s = AgreementSense(frozenset({"utilization", "use"}), prop, scope="all", min_votes=1)
    cov = pair_coverage(s, ["utilization->usage"])
    assert cov["rows"][0]["gold_votes"] == 2 and cov["rows"][0]["top_is_gold"]
    assert cov["summary"]["gold_2plus"] == 1 and cov["summary"]["top2_is_wrong"] == 0


def test_committed_coverage_numbers():
    cov = _post()["coverage"]
    assert cov["dev"]["summary"] == {"pairs": 57, "gold_2plus": 8, "gold_3plus": 3, "top2_is_gold": 7, "top2_is_wrong": 22}
    assert cov["heldout"]["summary"] == {"pairs": 53, "gold_2plus": 8, "gold_3plus": 3, "top2_is_gold": 7, "top2_is_wrong": 11}


def test_no_resource_consensus_on_the_ops_senses_the_readme_names():
    w = _post()["watch"]
    assert w["restart->bounce"]["gold_votes"] == 0 and w["restart->reboot"]["gold_votes"] == 0
    assert w["latency->lag"]["gold_votes"] == 1 and w["cadence->frequency"]["gold_votes"] == 1


def test_half_of_the_lone_gains_ride_on_a_wrong_sense():
    g = {r["id"]: {m["token"]: m["alts"] for m in r["mapped"]} for r in _post()["gained"]["agree2_lone"]}
    assert g["d4-06"] == {"chief": ["executive"]}
    assert g["d4-22"] == {"itinerary": ["path"]}
    assert g["d8-28"] == {"customers": ["consumer"]}
    assert g["d2-13"] == {"situation": ["status"]}
