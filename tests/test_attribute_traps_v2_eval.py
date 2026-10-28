"""Shipped default on the spent v2 traps: at2-01 was a known open (strict xfail) until 2026-10-28."""

import json
from dataclasses import replace
from pathlib import Path

from ops_copilot.attribute_traps_v2 import load_traps_v2
from ops_copilot.config import CopilotConfig
from ops_copilot.pipeline import Copilot

ROOT = Path(__file__).resolve().parents[1]


def test_report_records_exactly_the_known_open():
    rep = json.loads((ROOT / "artifacts" / "attribute_traps_v2_eval.json").read_text())
    assert rep["split_sizes"] == {"tune": 20, "confirm": 20} and rep["heldout_words_in_file"] == []
    assert rep["shipped_default"]["opened"] == [] == rep["known_open"]


def test_every_other_v2_trap_is_refused_by_the_shipped_default():
    bot = Copilot(config=CopilotConfig())
    opened = [r["id"] for r in load_traps_v2() if bot.ask(r["query"]).decision.value in ("ANSWER", "PROPOSE_WRITE")]
    assert opened == []


def test_at2_01_taste_of_the_flag_is_refused():
    # Was a strict xfail (2026-10-27: taste <- one passed the null test). Closed
    # 2026-10-28 by the credited-word check ("one" is a stop word); the pre-change
    # default still answers it.
    q = "What taste is the LaunchDarkly checkout_retry flag?"
    assert Copilot(config=CopilotConfig()).ask(q).decision.value.startswith("REFUSE_")
    pre = replace(CopilotConfig(), passage_support_credit_stop=False)
    assert Copilot(config=pre).ask(q).decision.value == "ANSWER"
