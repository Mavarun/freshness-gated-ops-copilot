"""Stack Exchange identifier false-positive set: harvest, split, scoring."""

from __future__ import annotations

import gzip
import json

from ops_copilot.passphrase import CUED_PASSPHRASE, CuedPassphraseDetector
from ops_copilot.passphrase_identifiers import harvest, score_identifiers, se_identifiers


def test_harvest_takes_3_to_6_part_names_only() -> None:
    got = harvest(["install xserver-xorg-input-libinput and set innodb_buffer_pool, see a-b or foo-bar",
                   "go to mysignins.microsoft.com. Then /etc/nginx/sites-enabled/default.conf"])
    assert got == {"xserver-xorg-input-libinput", "innodb_buffer_pool", "mysignins.microsoft.com"}


def test_split_is_disjoint_and_uses_the_qa_hash(tmp_path) -> None:
    from ops_copilot.qa_translation import is_test

    qid_train = next(i for i in range(1, 500) if not is_test("serverfault", i))
    qid_test = next(i for i in range(1, 500) if is_test("serverfault", i))
    items = [
        {"question_id": qid_train, "title": "shared-name-here and train-only-name", "answers": []},
        {"question_id": qid_test, "title": "shared-name-here and test-only-name", "answers": [{"body_markdown": "x"}]},
    ]
    (tmp_path / "serverfault-activity-p01.json.gz").write_bytes(gzip.compress(json.dumps({"items": items}).encode()))
    got = se_identifiers(tmp_path)
    assert got == {"train": ["shared-name-here", "train-only-name"], "test": ["test-only-name"]}


def test_score_counts_new_flags_against_a_base() -> None:
    names = ["elderly-service-semantic-clean", "proxy-cache-path-nginx", "marble-meadow-lagoon-badger"]
    old = CuedPassphraseDetector(wordlist_compounds=None)
    base = set(n for n in names if old.search(f"token {n}"))
    res = score_identifiers(CUED_PASSPHRASE, names, base=base)
    assert res["n"] == 3 and res["new_examples"] == ["elderly-service-semantic-clean"] and res["new_flags"] == 1
