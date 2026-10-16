"""Hand-written resources must not author held-out synonym words."""

from __future__ import annotations

import json
from pathlib import Path

from ops_copilot.resource_audit import HAND_WRITTEN, audit


def test_hand_written_resources_contain_no_heldout_word() -> None:
    found = {k: v for k, v in audit().items() if v}
    assert not found, found


def test_audit_detects_a_contaminated_seed(tmp_path: Path) -> None:
    seed = tmp_path / "seed.json"
    seed.write_text(
        json.dumps({"senses": [{"word": "lag", "gloss": "Delay in processing."}]}),
        encoding="utf-8",
    )
    assert audit(("seed.json",), root=tmp_path) == {"seed.json": ["lag"]}


def test_audit_ignores_meta_block(tmp_path: Path) -> None:
    seed = tmp_path / "seed.json"
    seed.write_text(
        json.dumps({"meta": {"purpose": "no lag, health, state"}, "senses": []}),
        encoding="utf-8",
    )
    assert audit(("seed.json",), root=tmp_path) == {"seed.json": []}


def test_every_audited_path_exists() -> None:
    root = Path(__file__).resolve().parents[1]
    for rel in HAND_WRITTEN:
        assert (root / rel).exists(), rel
