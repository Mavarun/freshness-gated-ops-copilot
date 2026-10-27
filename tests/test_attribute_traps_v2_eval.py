"""Shipped default on the spent v2 traps: one known open, pinned by a strict xfail."""

import json
from pathlib import Path

import pytest

from ops_copilot.attribute_traps_v2 import load_traps_v2
from ops_copilot.config import CopilotConfig
from ops_copilot.pipeline import Copilot

ROOT = Path(__file__).resolve().parents[1]


def test_report_records_exactly_the_known_open():
    rep = json.loads((ROOT / "artifacts" / "attribute_traps_v2_eval.json").read_text())
    assert rep["split_sizes"] == {"tune": 20, "confirm": 20} and rep["heldout_words_in_file"] == []
    assert rep["shipped_default"]["opened"] == ["at2-01"] == rep["known_open"]


def test_every_other_v2_trap_is_refused_by_the_shipped_default():
    bot = Copilot(config=CopilotConfig())
    opened = [r["id"] for r in load_traps_v2() if bot.ask(r["query"]).decision.value in ("ANSWER", "PROPOSE_WRITE")]
    assert set(opened) <= {"at2-01"}


@pytest.mark.xfail(strict=True, reason="known open (2026-10-27): passage rescue taste <- one passes the null "
                                       "test (sample 0.35 / 0.64; pool 0.408 / 0.646); no shipped fix yet")
def test_at2_01_taste_of_the_flag_is_refused():
    q = "What taste is the LaunchDarkly checkout_retry flag?"
    assert Copilot(config=CopilotConfig()).ask(q).decision.value.startswith("REFUSE_")
