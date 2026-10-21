"""Datamuse expand_known knob (default keeps the original behaviour) and the post-hoc record."""

import json
from pathlib import Path

from ops_copilot.config import CopilotConfig
from ops_copilot.datamuse_senses import DatamuseSense, DatamuseTable
from ops_copilot.pipeline import Copilot

TABLE = DatamuseTable(
    meta={"corpus_words": ["revert", "rollback", "returning", "latency"]},
    neighbours={
        "revert": (("returning", 2, False, "rev"), ("rollback", 5, True, "rev")),
        "delay": (("latency", 9, True, "rev"),),
    },
)
ART = Path(__file__).resolve().parents[1] / "artifacts" / "datamuse_dev3_posthoc.json"


def test_default_expands_known_words_and_off_maps_unknown_words_only():
    on = DatamuseSense(table=TABLE, max_rank=10, max_neighbours=2)
    assert [n.word for n in on.neighbours("revert")] == ["returning", "rollback"]
    off = DatamuseSense(table=TABLE, max_rank=10, max_neighbours=2, expand_known=False)
    assert off.neighbours("revert") == ()
    assert [n.word for n in off.neighbours("delay")] == ["latency"]


def test_config_default_and_pipeline_wiring():
    assert CopilotConfig().datamuse_expand_known is True
    bot = Copilot(config=CopilotConfig(use_datamuse_ml=True, datamuse_scope="lone", datamuse_expand_known=False))
    assert bot.datamuse.expand_known is False


def test_unknown_only_closes_the_revert_trap_in_the_post_hoc_run():
    arms = json.loads(ART.read_text())["arms"]
    assert json.loads(ART.read_text())["post_hoc"] is True
    full, unk = arms["dev3-chosen"], arms["dev3-chosen, unknown words only"]
    assert full["sweep_labelled_trap_opened"] and unk["sweep_labelled_trap_opened"] == []
    assert (unk["confirm"], unk["heldout_answer"], unk["clean"], unk["fail_open"]) == ("13/20", 0, 1.0, 0)
    assert full["confirm"] == "14/20" and arms["off"]["confirm"] == "11/20"
