import gzip
import hashlib

from ops_copilot.dupe_paraphrase import BUILD_MAX_PER_WORD, BUILD_MIN_CROSS, DEFAULT_TABLE, load_table

PAYLOAD_SHA256 = "3e1020d9800d1ed93a6bb8dfcafca38eb05431b1957f75c1072c701c1d6712a2"
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


def test_columnar_storage_round_trips_the_capped_rows():
    from ops_copilot.dupe_paraphrase import _columnar, _rows

    t = load_table()
    assert _rows(_columnar(t.rows)) == t.rows
    assert DEFAULT_TABLE.stat().st_size < 512 * 1024  # test_third_party_data's no-raw-dump guard


def test_no_titles_or_ids_are_stored():
    import json
    import re

    body = json.loads(gzip.decompress(DEFAULT_TABLE.read_bytes()))
    assert set(body) == {"meta", "n_pairs", "pairs"}
    assert set(body["meta"]) == {"source", "license", "sites", "archives_sha256", "n_words"}
    assert all(re.fullmatch(r"[a-z]{3,40}", w) for w in body["pairs"]["words"])


def test_notice_attributes_every_site_and_the_licence():
    notice = (DEFAULT_TABLE.parent / "NOTICE.md").read_text()
    assert DEFAULT_TABLE.name in notice and "Stack Exchange Inc." in notice
    assert "CC BY-SA 4.0" in notice and "creativecommons.org/licenses/by-sa/4.0" in notice
    assert "MIT licence covers" in notice
    for host in ("serverfault.com", "superuser.com", "unix.stackexchange.com", "askubuntu.com",
                 "dba.stackexchange.com", "security.stackexchange.com", "devops.stackexchange.com",
                 "networkengineering.stackexchange.com"):
        assert host in notice
