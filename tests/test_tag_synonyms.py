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
