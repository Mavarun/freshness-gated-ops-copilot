"""dev6 post-hoc mapping diagnosis: pinned and consistent with the recorded confirm."""

import json
from pathlib import Path

ART = Path(__file__).resolve().parents[1] / "artifacts"


def _out() -> dict:
    return json.loads((ART / "datamuse_dev6_posthoc.json").read_text())


def test_counts_are_pinned():
    o = _out()
    assert (o["n_rows"], o["n_swap_rows"], o["n_swap_rows_with_unknown_word"]) == (45, 36, 33)
    assert o["n_rows_mapped"] == 8
    assert (o["n_mappings_right_sense"], o["n_mappings_wrong_sense"]) == (3, 5)
    assert o["n_mapped_and_decision_changed"] == 4


def test_the_trap_opens_through_a_dictionary_synonym_used_in_the_wrong_sense():
    rows = {r["id"]: r for r in _out()["rows"]}
    (m,) = rows["d6-36"]["mappings"]
    assert (m["query_word"], m["corpus_word"], m["rank"], m["sense"]) == ("country", "region", 12, "wrong")
    assert m["cosine"] >= 0.30 and m["context"] >= 2  # passes both gates the arm has
    assert (rows["d6-36"]["off"], rows["d6-36"]["on"]) == ("REFUSE_UNGROUNDED", "ANSWER")


def test_one_of_the_three_fixes_is_right_for_the_wrong_reason():
    conf = json.loads((ART / "datamuse_dev6_confirm.json").read_text())["confirm"]
    rows = {r["id"]: r for r in _out()["rows"]}
    senses = {i: rows[i]["mappings"][0]["sense"] for i in conf["fixed"]}
    assert senses == {"d6-11": "right", "d6-24": "right", "d6-27": "wrong"}
    for r in rows.values():
        assert r["on"] == conf["on"]["decisions"][r["id"]] and r["off"] == conf["off"]["decisions"][r["id"]]
        if not r["mappings"]:
            assert r["on"] == r["off"], r["id"]
