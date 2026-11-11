import dataclasses

from ops_copilot.config import CopilotConfig
from ops_copilot.pipeline import Copilot
from ops_copilot.resource_agreement import AgreementSense


def test_off_by_default():
    cfg = CopilotConfig()
    assert cfg.use_resource_agreement is False
    assert Copilot().agreement is None


def test_wired_into_the_noun_slot_with_known_alts():
    cfg = dataclasses.replace(CopilotConfig(), use_resource_agreement=True, agreement_min_votes=3)
    bot = Copilot(config=cfg)
    assert isinstance(bot.agreement, AgreementSense)
    assert bot.agreement.min_votes == 3 and bot.agreement.scope == "known"
    assert bot.grounder.noun_gloss is bot.agreement
    assert bot.grounder.noun_gloss_known is True


def test_known_scope_stays_out_of_the_retrieval_rewrite():
    bot = Copilot(config=dataclasses.replace(CopilotConfig(), use_resource_agreement=True))
    assert bot.retriever.noun_gloss is None
    bot_all = Copilot(config=dataclasses.replace(CopilotConfig(), use_resource_agreement=True, agreement_scope="all"))
    assert bot_all.retriever.noun_gloss is bot_all.agreement
