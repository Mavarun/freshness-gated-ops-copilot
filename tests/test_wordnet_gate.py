"""WordNetNounSense gate: path, sibling fan-out and neighbour count (dev words only)."""

import pytest

from ops_copilot.wordnet_senses import WordNetNounSense, WordNetTable

TABLE = WordNetTable(
    meta={},
    neighbours={
        "widget": (
            ("gadget", "syn", 0, 0, 0),
            ("device", "hyper", 1, 0, 0),
            ("gizmo", "sib", 2, 5, 0),
            ("thing", "sib", 2, 300, 1),
        ),
    },
)


def words(b, tok="widget"):
    return [n.word for n in b.neighbours(tok)]


def test_path_gate():
    assert words(WordNetNounSense(max_path=0, max_neighbours=9, table=TABLE)) == ["gadget"]
    assert words(WordNetNounSense(max_path=1, max_neighbours=9, table=TABLE)) == ["gadget", "device"]


def test_sibling_fanout_gate():
    b = WordNetNounSense(max_path=2, max_fanout=10, max_neighbours=9, table=TABLE)
    assert words(b) == ["gadget", "device", "gizmo"]
    b = WordNetNounSense(max_path=2, max_fanout=1000, max_neighbours=9, table=TABLE)
    assert words(b)[-1] == "thing"


def test_neighbour_cap_and_sources():
    got = WordNetNounSense(max_path=2, max_neighbours=2, table=TABLE).neighbours("widget")
    assert [n.word for n in got] == ["gadget", "device"]
    assert [n.source for n in got] == ["wordnet_syn", "wordnet_hyper"]
    assert got[0].similarity > got[1].similarity


def test_identifiers_short_tokens_and_unknowns_return_nothing():
    b = WordNetNounSense(max_path=2, max_neighbours=9, table=TABLE)
    assert b.neighbours("ab") == ()
    assert b.neighbours("INC-4821") == ()
    assert b.neighbours("nothing") == ()


def test_bad_path_rejected():
    with pytest.raises(ValueError):
        WordNetNounSense(max_path=3, table=TABLE)


def test_real_table_dev_words():
    """Dev split words only (never held-out): WordNet senses for ops nouns."""
    b = WordNetNounSense(max_path=1, max_neighbours=2)
    assert "utilization" in words(b, "usage")
    assert words(b, "upkeep")[0] == "maintenance"
    assert "status" in words(b, "saturation")
