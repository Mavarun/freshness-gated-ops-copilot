"""The contact-channel post-hoc artifact recomputes, and its reading holds."""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
POST = json.loads((ROOT / "artifacts" / "contact_channel_posthoc.json").read_text())


def test_fresh_run_matches():
    from run_contact_channel_posthoc import run

    assert run() == POST


def test_every_remaining_miss_is_grounding_not_pii():
    assert POST["wrong_under_channel"] == ["f-cc02", "f-cc05", "f-cc07", "f-cc09", "f-cc10", "f-cc12"]
    assert POST["wrong_by_gate"] == {"grounding": 6, "pii": 0}


def test_cc12_pii_refusal_named_the_contact_page_not_the_owner_page():
    assert POST["pii_refusal_on_contact_page_for_owner_question"] == ["f-cc12"]
    row = next(x for x in POST["rows"] if x["id"] == "f-cc12")
    assert row["channel"]["missing"] == ["owner"]
    assert "pii_vault_transit_owner_directory" not in row["phrases"]["evidence"] + row["channel"]["evidence"]
