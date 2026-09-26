from __future__ import annotations

import json

from ops_copilot.eval import load_golden
from ops_copilot.paraphrase_set import (
    CARRY_FIELDS,
    DEFAULT_PARAPHRASE,
    build_paraphrase_set,
    load_paraphrase_set,
)
from ops_copilot.perturb import PERTURBATION_TYPES


def test_committed_paraphrase_file_matches_generator() -> None:
    rows = build_paraphrase_set(load_golden())
    expected = "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows)
    assert DEFAULT_PARAPHRASE.read_text(encoding="utf-8") == expected


def test_labels_and_session_fields_preserved() -> None:
    golden = load_golden()
    rows = load_paraphrase_set()
    assert len(rows) >= 3 * len(golden)
    for row in rows:
        src = golden[row["source_index"]]
        assert row["expect_decision"] == src["expect_decision"]
        assert row["perturbation"] in PERTURBATION_TYPES
        assert row["query"] != src["query"]
        for key in CARRY_FIELDS:
            assert row.get(key) == src.get(key)


def test_ids_are_unique_and_every_case_is_covered() -> None:
    golden = load_golden()
    rows = load_paraphrase_set()
    assert len({r["id"] for r in rows}) == len(rows)
    assert {r["source_index"] for r in rows} == set(range(len(golden)))
