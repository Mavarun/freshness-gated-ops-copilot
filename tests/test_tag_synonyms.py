"""Stack Exchange tag-synonym snapshot: provenance, integrity, no eval filtering."""

from __future__ import annotations

from collections import Counter

from ops_copilot.tag_synonyms import (
    OPS_SITES,
    SITES,
    SNAPSHOT_N_PAIRS,
    SNAPSHOT_SHA256,
    dump_snapshot,
    load_snapshot,
)


def test_snapshot_is_the_pinned_fetch():
    snap = load_snapshot()
    assert snap["sha256"] == SNAPSHOT_SHA256
    assert len(snap["pairs"]) == SNAPSHOT_N_PAIRS == snap["meta"]["n_pairs"]
    assert snap["meta"]["sites"] == list(SITES)
    assert "CC BY-SA" in snap["meta"]["license"]


def test_every_ops_site_is_complete_and_only_stackoverflow_is_cut():
    snap = load_snapshot()
    per_site = Counter(p["site"] for p in snap["pairs"])
    assert set(per_site) == set(SITES)
    assert snap["meta"]["truncated"] == ["stackoverflow"]
    assert per_site["stackoverflow"] == 2500
    # The ops sites were fetched whole (all well under the 2,500-row cap).
    assert all(per_site[s] < 2500 for s in OPS_SITES)
    assert per_site == Counter(snap["meta"]["per_site"])


def test_snapshot_rows_are_raw_tags():
    snap = load_snapshot()
    for p in snap["pairs"]:
        assert set(p) == {"site", "from_tag", "to_tag", "applied_count"}
        assert p["from_tag"] != p["to_tag"]
        assert p["from_tag"] == p["from_tag"].lower()
        assert p["applied_count"] >= 0
    # Unfiltered: tags unrelated to this corpus are kept as fetched.
    tags = {p["to_tag"] for p in snap["pairs"]}
    assert "reactjs" in tags


def test_dump_is_byte_stable(tmp_path):
    snap = load_snapshot()
    meta = {k: v for k, v in snap["meta"].items() if k not in ("n_pairs", "per_site")}
    a, b = tmp_path / "a.json.gz", tmp_path / "b.json.gz"
    da = dump_snapshot(list(reversed(snap["pairs"])), meta, a)
    db = dump_snapshot(snap["pairs"], meta, b)
    assert da == db == SNAPSHOT_SHA256
    assert a.read_bytes() == b.read_bytes()


# --- substitute table and backoff ---------------------------------------------

import pytest  # noqa: E402

from ops_copilot.corpus import Corpus  # noqa: E402
from ops_copilot.tag_synonyms import (  # noqa: E402
    TagSynonymBackoff,
    build_substitute_table,
    is_inflection,
    site_clusters,
    tag_word,
)

TOY = [
    {"site": "serverfault", "from_tag": "reboots", "to_tag": "restart", "applied_count": 3},
    {"site": "serverfault", "from_tag": "web-server", "to_tag": "webserver", "applied_count": 9},
    {"site": "superuser", "from_tag": "reboot", "to_tag": "restart", "applied_count": 0},
    {"site": "superuser", "from_tag": "cpu", "to_tag": "processor", "applied_count": 1},
    {"site": "unix", "from_tag": "boot", "to_tag": "startup", "applied_count": 1},
]


def test_tag_word_only_plain_single_words():
    assert tag_word("restart") == "restart"
    assert tag_word("web-server") is None
    assert tag_word("c#") is None
    assert tag_word("ip") is None  # too short to look up
    assert tag_word("python-3.x") is None


def test_clusters_are_per_site_and_star_shaped():
    cl = site_clusters(TOY)
    assert ("serverfault", frozenset({"restart", "reboots"})) in cl
    assert ("superuser", frozenset({"restart", "reboot"})) in cl
    # min_applied drops rarely-applied synonyms
    cl1 = site_clusters(TOY, min_applied=1)
    assert ("superuser", frozenset({"restart", "reboot"})) not in cl1
    assert all(site != "superuser" or "cpu" in tags for site, tags in cl1)


def test_table_counts_sites_and_folds_plurals():
    table = build_substitute_table(TOY, {"restart", "cpu", "startup"})
    # 'reboots' (serverfault) folds to 'reboot', but votes are keyed by surface
    assert table["reboots"] == (("restart", 1),)
    assert table["reboot"] == (("restart", 1),)
    assert table["processor"] == (("cpu", 1),)
    assert table["boot"] == (("startup", 1),)
    # a corpus word maps to the other corpus words of its cluster only
    assert "restart" not in table  # no other corpus word in its clusters
    only_ops = build_substitute_table(TOY, {"restart"}, sites=("serverfault",))
    assert set(only_ops) == {"reboots"}


def test_table_never_maps_a_word_to_its_own_inflection():
    pairs = [{"site": "dba", "from_tag": "indexes", "to_tag": "index", "applied_count": 5}]
    table = build_substitute_table(pairs, {"index", "indexes"})
    assert table == {}
    assert is_inflection("debug", "debugging")
    assert is_inflection("hook", "hooks")
    assert is_inflection("states", "state")
    assert is_inflection("archives", "archive")
    assert is_inflection("cached", "cache")
    assert is_inflection("rotate", "rotating")
    assert not is_inflection("restart", "reboot")
    assert not is_inflection("cpu", "processor")


def _texts():
    return [f"{c.title} {c.text}" for c in Corpus().chunks]


def test_backoff_on_snapshot_is_deterministic_and_corpus_bound():
    a = TagSynonymBackoff(_texts(), max_neighbours=3)
    b = TagSynonymBackoff(_texts(), max_neighbours=3, snapshot=load_snapshot())
    assert a.table == b.table
    assert a.table, "the snapshot reaches at least some corpus words"
    for word, rows in a.table.items():
        for target, n_sites in rows:
            assert target in a.corpus_words and target != word
            assert 1 <= n_sites <= len(SITES)


def test_backoff_skips_identifiers_numbers_and_short_tokens():
    bk = TagSynonymBackoff(_texts(), max_neighbours=3)
    for tok in ("p99", "checkout-api", "2410", "db", "cnry-vault7f3a"):
        assert bk.neighbours(tok) == ()


def test_backoff_min_sites_and_neighbour_cap():
    bk1 = TagSynonymBackoff(_texts(), max_neighbours=5)
    bk2 = TagSynonymBackoff(_texts(), max_neighbours=5, min_sites=2)
    multi = [w for w, rows in bk1.table.items() if len(rows) > 1]
    for w in multi:
        assert len(TagSynonymBackoff(_texts(), max_neighbours=1).neighbours(w)) == 1
    for w in bk1.table:
        assert all(n.similarity >= 2 for n in bk2.neighbours(w))
        assert all(n.source == "tagsyn" for n in bk1.neighbours(w))


def test_backoff_rejects_unknown_sites():
    with pytest.raises(ValueError):
        TagSynonymBackoff(_texts(), sites=("cooking",))
