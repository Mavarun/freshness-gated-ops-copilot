"""Committed outside data: attribution, licence and "no raw dumps" guards.

Every snapshot fetched from Stack Exchange carries its CC BY-SA licence and
attribution in ``meta`` and in a NOTICE.md next to it, and the QA translation
table holds word statistics only (no post text). Large raw dumps stay out.
"""

from __future__ import annotations

import gzip
import json
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
SE_SNAPSHOTS = [
    DATA / "qa" / "se_qa_translation.json.gz",
    DATA / "tagsyn" / "stackexchange_tag_synonyms.json.gz",
]
# Hosts of the API site parameters used by the fetch scripts.
SITE_HOSTS = {
    "serverfault": "serverfault.com",
    "superuser": "superuser.com",
    "unix": "unix.stackexchange.com",
    "askubuntu": "askubuntu.com",
    "dba": "dba.stackexchange.com",
    "security": "security.stackexchange.com",
    "devops": "devops.stackexchange.com",
    "networkengineering": "networkengineering.stackexchange.com",
}
MAX_COMMITTED_BYTES = 512 * 1024


def _meta(path: Path) -> dict:
    return json.loads(gzip.decompress(path.read_bytes()))["meta"]


@pytest.mark.parametrize("path", SE_SNAPSHOTS, ids=lambda p: p.parent.name)
def test_stack_exchange_snapshot_carries_licence_and_notice(path: Path) -> None:
    meta = _meta(path)
    assert "CC BY-SA 4.0" in meta["license"]
    assert meta["source_url"].startswith("https://api.stackexchange.com/2.3/")
    notice = (path.parent / "NOTICE.md").read_text()
    assert path.name in notice
    assert "CC BY-SA 4.0" in notice and "creativecommons.org/licenses/by-sa/4.0" in notice
    assert "Stack Exchange Inc." in notice
    assert "MIT licence covers" in notice


def test_qa_notice_and_meta_attribute_every_site_and_input_licence() -> None:
    path = SE_SNAPSHOTS[0]
    meta = _meta(path)
    notice = (path.parent / "NOTICE.md").read_text()
    for site in meta["sites"]:
        assert SITE_HOSTS[site] in meta["attribution"]
        assert SITE_HOSTS[site] in notice
    assert set(meta["licenses"]) == {"CC BY-SA 2.5", "CC BY-SA 3.0", "CC BY-SA 4.0"}
    for lic, n in meta["licenses"].items():
        assert f"{lic.split()[-1]}: {n:,}" in notice
    assert meta["license_url"] == "https://creativecommons.org/licenses/by-sa/4.0/"
    assert "sort=activity" in meta["source"]  # both slices the fetch script reads


def test_qa_table_holds_word_statistics_only() -> None:
    table = json.loads(gzip.decompress(SE_SNAPSHOTS[0].read_bytes()))["table"]
    words = set(table)
    for rows in table.values():
        for row in rows:
            assert len(row) == 4
            assert all(isinstance(x, (int, float)) for x in row[1:])
            words.add(row[0])
    # plain lowercase tokens, no sentences, links, user names or code
    assert all(re.fullmatch(r"[a-z0-9]{1,24}", w) for w in words)


def test_no_large_raw_dumps_committed() -> None:
    big = [
        str(p.relative_to(ROOT))
        for top in ("data", "artifacts")
        for p in (ROOT / top).rglob("*")
        if p.is_file() and p.name != "traces.jsonl"  # gitignored runtime log
        and p.stat().st_size > MAX_COMMITTED_BYTES
    ]
    assert big == []
    assert not list(DATA.rglob("*-p[0-9][0-9].json.gz"))  # raw fetch pages stay outside


def test_readme_licence_section_points_to_the_notices() -> None:
    readme = (ROOT / "README.md").read_text()
    section = readme[readme.index("## License") :]
    for path in SE_SNAPSHOTS:
        assert str((path.parent / "NOTICE.md").relative_to(ROOT)) in section
