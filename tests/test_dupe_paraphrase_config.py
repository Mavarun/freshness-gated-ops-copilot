import dataclasses

import pytest

from ops_copilot.config import CopilotConfig
from ops_copilot.dupe_paraphrase import DupeParaphraseSense
from ops_copilot.pipeline import Copilot


def test_off_by_default():
    cfg = CopilotConfig()
    assert cfg.use_dupe_paraphrase is False
    assert Copilot().dupe is None


def test_wired_into_the_noun_slot_with_known_alts():
    cfg = dataclasses.replace(CopilotConfig(), use_dupe_paraphrase=True, dupe_min_cross=4, dupe_min_g2=10.83)
    bot = Copilot(config=cfg)
    assert isinstance(bot.dupe, DupeParaphraseSense)
    assert bot.dupe.min_cross == 4 and bot.dupe.min_g2 == 10.83 and bot.dupe.scope == "known"
    assert bot.grounder.noun_gloss is bot.dupe
    assert bot.grounder.noun_gloss_known is True


def test_known_scope_stays_out_of_the_retrieval_rewrite():
    bot = Copilot(config=dataclasses.replace(CopilotConfig(), use_dupe_paraphrase=True))
    assert bot.retriever.noun_gloss is None
    bot_all = Copilot(config=dataclasses.replace(CopilotConfig(), use_dupe_paraphrase=True, dupe_scope="all"))
    assert bot_all.retriever.noun_gloss is bot_all.dupe


def test_bad_scope_is_rejected():
    with pytest.raises(ValueError):
        Copilot(config=dataclasses.replace(CopilotConfig(), use_dupe_paraphrase=True, dupe_scope="some"))


def test_chained_after_resource_agreement():
    cfg = dataclasses.replace(CopilotConfig(), use_dupe_paraphrase=True, use_resource_agreement=True)
    bot = Copilot(config=cfg)
    assert bot.grounder.noun_gloss.parts == (bot.agreement, bot.dupe)


def test_off_changes_no_golden_decision():
    import json
    from pathlib import Path

    rows = [json.loads(x) for x in (Path(__file__).resolve().parents[1] / "data/golden/questions.jsonl").read_text().splitlines() if x.strip()]
    ref = Copilot()
    off = Copilot(config=dataclasses.replace(CopilotConfig(), use_dupe_paraphrase=False, dupe_scope="all", dupe_min_cross=9))
    assert [off.ask(r["query"]).decision for r in rows] == [ref.ask(r["query"]).decision for r in rows]
