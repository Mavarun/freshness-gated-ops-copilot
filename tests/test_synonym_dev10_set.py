from collections import Counter

from ops_copilot.synonym_dev10 import load_dev10, must_refuse_rows, vocabulary_problems


def test_size_and_labels():
    rows = load_dev10()
    assert len(rows) == 26
    c = Counter(r["expect_decision"] for r in rows)
    assert c == {"ANSWER": 15, "REFUSE_STALE": 2, "REFUSE_UNGROUNDED": 7, "REFUSE_NO_EVIDENCE": 2}
    assert len(must_refuse_rows(rows)) == 11
    assert len({r["id"] for r in rows}) == 26


def test_guard_is_clean():
    assert vocabulary_problems() == {}


def test_guard_catches_a_held_out_word_and_a_dev7_word():
    bad = [
        {"id": "x1", "source_index": 0, "query": "What is the current checkout p99 lag?", "expect_decision": "ANSWER", "swap": "latency -> lag"},
        {"id": "x2", "source_index": 0, "query": "What is the current checkout p99 sluggishness?", "expect_decision": "ANSWER", "swap": "latency -> sluggishness"},
    ]
    probs = vocabulary_problems(bad)
    assert any(p.startswith("heldout:") for p in probs["x1"])
    assert "shared_dev7:sluggishness" in probs["x2"]


def test_every_swap_row_points_at_a_golden_query_with_the_same_label():
    import json
    from pathlib import Path

    golden = [json.loads(x) for x in (Path(__file__).resolve().parents[1] / "data/golden/questions.jsonl").read_text().splitlines() if x.strip()]
    for r in load_dev10():
        if "swap" in r:
            assert golden[r["source_index"]]["expect_decision"] == r["expect_decision"], r["id"]
        else:
            assert r["expect_decision"] == "REFUSE_UNGROUNDED" and "trap" in r
