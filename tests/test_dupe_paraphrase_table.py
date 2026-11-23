import gzip
import hashlib

from ops_copilot.dupe_paraphrase import BUILD_MAX_PER_WORD, BUILD_MIN_CROSS, DEFAULT_TABLE, load_table

PAYLOAD_SHA256 = "f4ccb9763b1529e38d399b1df25cd2a7d3789329d90d4f5f6ade52e5f7bfe564"
SITES = {"askubuntu": 41931, "dba": 2190, "devops": 19, "networkengineering": 392, "security": 4649,
         "serverfault": 4953, "superuser": 14660, "unix": 10101}


def test_committed_table_is_pinned():
    payload = gzip.decompress(DEFAULT_TABLE.read_bytes())
    assert hashlib.sha256(payload).hexdigest() == PAYLOAD_SHA256


def test_meta_counts_and_licence():
    t = load_table()
    assert t.meta["sites"] == SITES and sum(SITES.values()) == t.n_pairs == 78895
    assert t.meta["n_words"] == len(t.rows) == 6255
    assert t.meta["license"] == "CC BY-SA 4.0" and len(t.meta["archives_sha256"]) == 8


def test_rows_respect_build_floor_and_cap():
    t = load_table()
    for w, rows in t.rows.items():
        assert 0 < len(rows) <= BUILD_MAX_PER_WORD
        assert all(r[2] >= BUILD_MIN_CROSS and r[1] >= 0 for r in rows)  # G² > 0 before rounding to 3 places
        assert w.isalpha() and w == w.lower()


def test_table_is_symmetric():
    t = load_table()
    pairs = {(w, r[0]): r[1:] for w, rows in t.rows.items() for r in rows}
    # a pair cut by one side's 40-partner cap may be missing from the other side; every
    # pair present on both sides carries the same numbers
    both = [(a, b) for (a, b) in pairs if (b, a) in pairs]
    assert len(both) > 10_000
    assert all(pairs[(a, b)] == pairs[(b, a)] for a, b in both)


def test_no_titles_or_ids_are_stored():
    t = load_table()
    assert all(" " not in w for w in t.rows)
    assert set(t.meta) == {"source", "license", "sites", "archives_sha256", "n_words"}
