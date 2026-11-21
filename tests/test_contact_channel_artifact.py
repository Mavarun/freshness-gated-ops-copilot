"""The committed contact-channel artifact is what a fresh run of the pre-registered rule gives."""

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
ART = json.loads((ROOT / "artifacts" / "contact_channel.json").read_text())


@pytest.fixture(scope="module")
def fresh():
    from run_contact_channel_protocol import run

    return run()


def test_fresh_run_matches(fresh):
    assert fresh == ART


def test_recorded_outcome():
    A, B = ART["regression"], ART["confirm"]
    assert A["n"] == 751 and B["n"] == 19
    assert A["correct"] == {"phrases": 509, "channel": 510}
    assert A["misfires"] == {"phrases": 11, "channel": 4}
    assert B["correct"] == {"phrases": 10, "channel": 13}
    assert B["misfires"] == {"phrases": 8, "channel": 0}
    assert len(A["changed"]) == 7 and ART["checks"]["ship"]


def test_only_d4_24_answers_and_nothing_opens():
    opened = [r["id"] for r in ART["regression"]["changed"] if r["channel"] == "ANSWER"]
    assert opened == ["d4-24"]
    assert all(r["expect"] == "ANSWER" for r in ART["regression"]["changed"])


def test_confirm_owner_email_loses_its_gate_but_stays_refused():
    row = next(r for r in ART["confirm"]["rows"] if r["id"] == "f-cc12")
    assert (row["phrases"], row["channel"]) == ("REFUSE_PII", "REFUSE_UNGROUNDED")
    assert not any(r["expect"] == "REFUSE_PII" and r["channel"] == "ANSWER" for r in ART["confirm"]["rows"])
