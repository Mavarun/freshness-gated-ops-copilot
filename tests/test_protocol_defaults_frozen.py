"""Pre-registered tie-break defaults are frozen literals, not read from the live config."""

import json
from dataclasses import replace
from pathlib import Path

from ops_copilot import datamuse_dev2, datamuse_dev3
from ops_copilot.config import CopilotConfig

ART = Path(__file__).resolve().parents[1] / "artifacts"
KEYS2 = ("scope", "max_rank", "max_neighbours", "noun_only")
KEYS3 = ("scope", "max_rank", "max_neighbours", "context_min")


def test_registered_defaults():
    assert datamuse_dev2.DEFAULTS == {"max_rank": 10, "max_neighbours": 1, "noun_only": False}
    assert datamuse_dev3.DEFAULTS == {"max_rank": 10, "max_neighbours": 1, "context_min": 0}


def test_committed_choices_replay_from_the_frozen_tie_break():
    for mod, name, keys in ((datamuse_dev2, "datamuse_dev2_calibration.json", KEYS2),
                            (datamuse_dev3, "datamuse_dev3_calibration.json", KEYS3)):
        rep = json.loads((ART / name).read_text())
        best = min(rep["results"], key=mod.selection_key)
        assert {k: best[k] for k in keys} == {k: rep["chosen"][k] for k in keys}, name


def test_a_changed_config_default_does_not_move_the_tie_break(monkeypatch):
    moved = replace(CopilotConfig(), datamuse_max_rank=50, datamuse_max_neighbours=2)
    monkeypatch.setattr(datamuse_dev3, "CopilotConfig", lambda **kw: replace(moved, **kw))
    r = {"safe": True, "calib_correct": 1, "calib_answer_correct": 1, "scope": "lone",
         "max_rank": 10, "max_neighbours": 1, "context_min": 0}
    assert datamuse_dev3.knobs_off_default(r) == 0
