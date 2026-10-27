"""The seed-free pool mode is an opt-in knob; the shipped seed-42 sample is untouched."""

from dataclasses import replace

from ops_copilot.attribute_traps import load_traps
from ops_copilot.config import CopilotConfig
from ops_copilot.passage_support import control_pool
from ops_copilot.pipeline import Copilot


def _pool_cfg(**kw):
    return replace(CopilotConfig(), passage_support_null_pool=True, **kw)


def test_pool_mode_is_off_by_default_and_the_default_still_draws_100_seed_42_controls():
    cfg = CopilotConfig()
    assert cfg.passage_support_null_pool is False
    g = Copilot(config=cfg).grounder
    assert len(g.passage_null_controls) == 100 and not g.passage_null_pool


def test_pool_mode_uses_the_whole_unsampled_pool_and_ignores_seed_and_count():
    g = Copilot(config=_pool_cfg()).grounder
    pool = g.passage_null_controls
    assert len(pool) > 4000 and list(pool) == sorted(set(pool))
    assert not set(pool) & set(g.idf)
    assert control_pool(g.passage_support.vectors, set(g.idf) - set(pool)) != ()
    for kw in ({"passage_support_null_seed": 7}, {"passage_support_null_controls": 300}):
        assert Copilot(config=_pool_cfg(**kw)).grounder.passage_null_controls == g.passage_null_controls
    assert set(Copilot(config=CopilotConfig()).grounder.passage_null_controls) <= set(g.passage_null_controls)


def test_pool_mode_decisions_do_not_depend_on_the_seed():
    rows = load_traps()[:12]
    d = {}
    for seed in (42, 3):
        bot = Copilot(config=_pool_cfg(passage_support_null_seed=seed))
        d[seed] = [bot.ask(r["query"]).decision.value for r in rows]
    assert d[42] == d[3]


def test_null_log_records_each_test_without_changing_a_decision():
    bot = Copilot(config=CopilotConfig())
    q = "What is the checkout error budget flavour?"
    dec = bot.ask(q).decision.value
    assert bot.grounder.null_log and all(e[0] == q and 0.0 <= e[2] <= 1.0 for e in bot.grounder.null_log)
    assert {e[1] for e in bot.grounder.null_log} == {"flavour"}
    assert dec == Copilot(config=CopilotConfig()).ask(q).decision.value
