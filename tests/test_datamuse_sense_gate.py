"""Datamuse word-meaning gate: off by default, drops candidates the vectors do not back."""

from __future__ import annotations

import pytest

from ops_copilot.config import CopilotConfig
from ops_copilot.datamuse_pair_sense import PairSenseTable
from ops_copilot.datamuse_senses import DatamuseSense, DatamuseTable
from ops_copilot.pipeline import Copilot

TABLE = DatamuseTable(
    meta={"corpus_words": ["duty", "schedule", "path", "latency"]},
    neighbours={
        "legal": (("duty", 21, True, "rev"),),
        "itinerary": (("path", 1, True, "rev"), ("schedule", 4, True, "rev")),
        "delay": (("latency", 3, True, "rev"),),
    },
)
PAIRS = PairSenseTable(
    meta={},
    pairs={"legal": {"duty": 0.26}, "itinerary": {"path": 0.77, "schedule": 0.21}, "delay": {"latency": None}},
)


def _sense(**kw) -> DatamuseSense:
    return DatamuseSense(table=TABLE, sense_table=PAIRS, max_rank=100, max_neighbours=2,
                         lone_unknown=True, expand_known=False, **kw)


def test_gate_off_keeps_the_original_candidates():
    s = _sense()
    assert [n.word for n in s.neighbours("legal")] == ["duty"]
    assert [n.word for n in s.neighbours("itinerary")] == ["path", "schedule"]


def test_gate_drops_low_cosine_and_missing_cosine_pairs():
    s = _sense(sense_min=0.3)
    assert s.neighbours("legal") == ()
    assert [n.word for n in s.neighbours("itinerary")] == ["path"]
    assert s.neighbours("delay") == ()  # no cosine (out of vocabulary) fails closed
    assert s.passes_sense("itinerary", "path") and not s.passes_sense("legal", "duty")


def test_gate_composes_with_the_context_gate():
    docs = (frozenset({"itinerary", "schedule", "rotation"}), frozenset({"path", "vault"}))
    s = _sense(sense_min=0.2, context_min=1, doc_words=docs)
    s.set_context(frozenset({"itinerary", "rotation"}))
    # schedule passes both gates; path passes the sense gate but shares no chunk with rotation
    assert [n.word for n in s.neighbours("itinerary")] == ["schedule"]


@pytest.mark.parametrize("bad", [-0.1, 1.5])
def test_out_of_range_threshold_is_rejected(bad):
    with pytest.raises(ValueError):
        _sense(sense_min=bad)


def test_config_default_is_off_and_pipeline_wires_the_committed_table():
    assert CopilotConfig().datamuse_sense_min == 0.0
    bot = Copilot(config=CopilotConfig(use_datamuse_ml=True, datamuse_scope="lone",
                                       datamuse_expand_known=False, datamuse_sense_min=0.3))
    assert bot.datamuse.sense_min == 0.3 and bot.datamuse.sense_table is not None
    assert bot.datamuse.sense_similarity("legal", "duty") == 0.26
