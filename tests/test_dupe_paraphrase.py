import gzip
import json

import pytest

from ops_copilot.dupe_paraphrase import (
    BUILD_MIN_CROSS,
    DupeParaphraseSense,
    DupeTable,
    build_table,
    duplicate_pairs,
    dump_table,
    g2,
    load_table,
    title_words,
)

# Synthetic titles: "wipe" replaces "erase" across pairs; "nginx" and "proxy" are topical
# neighbours that sit together inside titles.
PAIRS = (
    [("How do I wipe a disk", "How to erase a disk")] * 4
    + [("wipe partition table", "erase partition table")] * 2
    + [("nginx proxy timeout", "nginx proxy slow")] * 3
    + [("nginx config reload", "proxy config reload")] * 1
    + [("mount usb drive", "attach usb drive")] * 1
    + [(f"unrelated title {w}", f"unrelated title {w}") for w in "abcdefghij"]
)


def table():
    t = build_table(PAIRS)
    return DupeTable({}, t["n_pairs"], t["df"], t["rows"])


def test_title_words_are_plain_folded_content_words():
    assert title_words("How to restart 2 nginx-workers &amp; disks?") == frozenset({"restart", "disk"})


def test_shared_words_are_context_not_paraphrase():
    t = build_table([("wipe the disk", "erase the disk")] * 3 + [("list files", "show files")] * 3)
    assert "disk" not in t["rows"]
    assert [r[0] for r in t["rows"]["wipe"]] == ["erase"]


def test_cross_and_same_counts():
    t = table()
    row = {r[0]: r for r in t.get("wipe")}
    assert row["erase"][2] == 6 and row["erase"][3] == 0
    # one-off pairs stay below the build floor
    assert BUILD_MIN_CROSS == 2 and t.get("mount") == ()


def test_g2_positive_association_only():
    assert g2(5, 5, 5, 100) > 0
    assert g2(0, 10, 10, 100) == 0.0
    assert g2(1, 50, 50, 100) == 0.0


def test_lookup_is_symmetric():
    t = table()
    assert [r[0] for r in t.get("erase")][0] == "wipe"
    assert [r[0] for r in t.get("wipe")][0] == "erase"


def test_sense_gates_and_corpus_words():
    words = frozenset({"erase", "disk", "proxy", "wipe"})
    s = DupeParaphraseSense(words, table(), min_cross=3, min_g2=0.0, min_ratio=2.0, scope="all")
    assert [n.word for n in s.neighbours("wipe")] == ["erase"]
    # a candidate outside the corpus is never returned
    s2 = DupeParaphraseSense(frozenset({"disk"}), table(), min_cross=2, min_g2=0.0, scope="all")
    assert s2.neighbours("wipe") == ()
    # cross count floor
    assert DupeParaphraseSense(words, table(), min_cross=7, min_g2=0.0, scope="all").neighbours("wipe") == ()


def test_ratio_gate_drops_topical_neighbours():
    t = build_table([("nginx proxy timeout", "nginx proxy slow")] * 3 + [("nginx reload", "proxy reload")] * 3
                    + [("proxy nginx cache", "proxy nginx cache")] * 4)
    tab = DupeTable({}, t["n_pairs"], t["df"], t["rows"])
    row = {r[0]: r for r in tab.get("nginx")}
    assert row["proxy"][2] == 3 and row["proxy"][3] >= 3
    words = frozenset({"proxy", "nginx"})
    assert DupeParaphraseSense(words, tab, min_cross=2, min_g2=0.0, min_ratio=2.0, scope="all").neighbours("nginx") == ()
    assert DupeParaphraseSense(words, tab, min_cross=2, min_g2=0.0, min_ratio=0.0, scope="all").neighbours("nginx")


def test_scopes():
    words = frozenset({"erase", "disk"})
    known = DupeParaphraseSense(words, table(), min_cross=2, min_g2=0.0, scope="known")
    assert known.neighbours("wipe") == ()  # unknown word, known scope
    lone = DupeParaphraseSense(words, table(), min_cross=2, min_g2=0.0, scope="lone")
    assert lone.lone_unknown and [n.word for n in lone.neighbours("wipe")] == ["erase"]
    lone2 = DupeParaphraseSense(words, table(), min_cross=2, min_g2=0.0, scope="lone")
    lone2.set_suspend_unknown(True)
    assert lone2.neighbours("wipe") == ()
    with pytest.raises(ValueError):
        DupeParaphraseSense(words, table(), scope="nope")
    with pytest.raises(ValueError):
        DupeParaphraseSense(words, table(), min_cross=1)


def test_identifiers_and_short_tokens_are_never_looked_up():
    s = DupeParaphraseSense(frozenset({"erase"}), table(), min_cross=2, min_g2=0.0, scope="all")
    assert s.neighbours("p99") == () and s.neighbours("db") == () and s.neighbours("wipe-1") == ()


def test_duplicate_pairs_keeps_duplicate_closures_once():
    page = {"site": "sf", "items": [
        {"question_id": 1, "title": "a", "closed_reason": "Duplicate",
         "closed_details": {"original_questions": [{"question_id": 9, "title": "b"}]}},
        {"question_id": 1, "title": "a", "closed_reason": "Duplicate",
         "closed_details": {"original_questions": [{"question_id": 9, "title": "b"}]}},
        {"question_id": 2, "title": "c", "closed_reason": "off topic", "closed_details": {}},
    ]}
    assert duplicate_pairs([page]) == [("sf", 1, "a", "b")]


def test_dump_is_byte_stable_and_loads(tmp_path):
    t = build_table(PAIRS)
    a, b = tmp_path / "a.json.gz", tmp_path / "b.json.gz"
    assert dump_table(t, {"x": 1}, a) == dump_table(t, {"x": 1}, b)
    assert a.read_bytes() == b.read_bytes()
    loaded = load_table(a)
    assert loaded.meta == {"x": 1} and loaded.n_pairs == len(PAIRS)
    assert json.loads(gzip.decompress(a.read_bytes()))["rows"]["wipe"][0][0] == "erase"
