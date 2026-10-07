"""Tag-synonym backoff wiring: grounding terms, known-word scope, rewrite, config."""

from __future__ import annotations

from dataclasses import replace

import pytest

from ops_copilot import Copilot, CopilotConfig
from ops_copilot.config import CopilotConfig as Cfg
from ops_copilot.grounding import Grounder
from ops_copilot.retrieve import Retriever
from ops_copilot.corpus import Corpus
from ops_copilot.tag_synonyms import OPS_SITES, SITES, TagSynonymBackoff, tag_synonym_sites

TEXTS = [
    "Restart the payments worker after the deploy finishes.",
    "The cpu dashboard shows the worker queue.",
]
TOY = {
    "pairs": [
        {"site": "serverfault", "from_tag": "reboot", "to_tag": "restart", "applied_count": 4},
        {"site": "superuser", "from_tag": "processor", "to_tag": "cpu", "applied_count": 2},
        {"site": "unix", "from_tag": "processor", "to_tag": "cpu", "applied_count": 1},
        {"site": "unix", "from_tag": "dashboard", "to_tag": "worker", "applied_count": 1},
    ]
}


def _bk(**kw) -> TagSynonymBackoff:
    return TagSynonymBackoff(TEXTS, snapshot=TOY, **kw)


def _grounder(*, known: bool = False, **kw) -> Grounder:
    return Grounder(TEXTS, tagsyn=_bk(**kw), tagsyn_known=known)


def test_unknown_word_gets_its_tag_substitute_and_weight() -> None:
    g = _grounder()
    term = next(t for t in g.terms("How do we reboot the payments worker?") if t.token == "reboot")
    assert term.kind == "tagsyn"
    assert term.alts == frozenset({"reboot", "restart"})
    assert term.weight == g._weight("restart")
    assert g.support("How do we reboot the payments worker?", TEXTS[0]).ok(term)


def test_without_backoff_the_word_stays_unknown() -> None:
    term = next(t for t in Grounder(TEXTS).terms("reboot the worker") if t.token == "reboot")
    assert term.kind == "unknown" and term.alts == frozenset({"reboot"})


def test_known_word_scope_is_opt_in() -> None:
    q = "Where is the dashboard for the deploy?"
    off = next(t for t in _grounder().terms(q) if t.token == "dashboard")
    on = next(t for t in _grounder(known=True).terms(q) if t.token == "dashboard")
    assert off.kind == on.kind == "known"
    assert "worker" not in off.alts and "worker" in on.alts


def test_min_sites_filters_single_site_links() -> None:
    q = "reboot the processor"
    two = {t.token: t for t in _grounder(min_sites=2).terms(q)}
    assert two["processor"].kind == "tagsyn"  # superuser + unix
    assert two["reboot"].kind == "unknown"  # serverfault only


def test_identifiers_never_get_substitutes() -> None:
    q = "reboot payments-worker p99 300"
    on = {t.token: t for t in _grounder(known=True).terms(q)}
    for tok in ("payments-worker", "p99", "300"):
        assert on[tok].kind == "identifier"


def test_rewrite_replaces_unknown_word_with_tag_substitute() -> None:
    chunks = Corpus().chunks
    texts = [f"{c.title} {c.text}" for c in chunks]
    assert any("checkout" in t.lower() for t in texts)
    toy = {"pairs": [{"site": "serverfault", "from_tag": "till", "to_tag": "checkout", "applied_count": 1}]}
    bk = TagSynonymBackoff(texts, snapshot=toy)
    r_on = Retriever(chunks, Cfg(), tagsyn=bk)
    r_off = Retriever(chunks, Cfg())
    assert "checkout" in r_on.rewrite_query("the till latency").split()
    assert "till" in r_off.rewrite_query("the till latency").split()


def test_config_wires_the_backoff_and_defaults_off() -> None:
    assert Copilot().tagsyn is None
    bot = Copilot(config=replace(CopilotConfig(), use_tag_synonym_backoff=True, tag_synonym_sites="ops"))
    assert bot.tagsyn is not None and bot.tagsyn.sites == OPS_SITES
    assert bot.grounder.tagsyn is bot.tagsyn and bot.retriever.tagsyn is bot.tagsyn
    assert tag_synonym_sites("all") == SITES
    with pytest.raises(ValueError):
        tag_synonym_sites("everything")


# --- Wiktionary computing-sense backoff wiring ----------------------------------

from ops_copilot.wiktionary_senses import WiktionarySenseBackoff  # noqa: E402

WIKT = {
    "senses": [
        {"word": "bounce", "pos": "verb", "topic": "computing", "synonyms": [], "gloss": "To restart a worker."},
        {"word": "reboot", "pos": "verb", "topic": "computing", "synonyms": ["restart"], "gloss": "To boot again."},
        {"word": "board", "pos": "noun", "topic": "computing", "synonyms": ["dashboard"], "gloss": "A panel."},
    ]
}


def _wk(**kw) -> WiktionarySenseBackoff:
    return WiktionarySenseBackoff(TEXTS, extract=WIKT, **kw)


def test_wiktionary_term_kind_weight_and_min_score() -> None:
    g = Grounder(TEXTS, wiktionary=_wk())
    t = {x.token: x for x in g.terms("bounce the worker")}["bounce"]
    assert t.kind == "wiktionary" and t.alts == frozenset({"bounce", "restart"})
    assert t.weight == g._weight("restart")
    strict = Grounder(TEXTS, wiktionary=_wk(min_score=2))
    s = {x.token: x for x in strict.terms("bounce or reboot the worker")}
    assert s["bounce"].kind == "unknown"  # gloss head only (score 1)
    assert s["reboot"].kind == "wiktionary"  # listed synonym (score 2)


def test_tag_synonyms_run_before_wiktionary() -> None:
    g = Grounder(TEXTS, tagsyn=_bk(), wiktionary=_wk())
    assert {x.token: x for x in g.terms("reboot the worker")}["reboot"].kind == "tagsyn"


def test_wiktionary_known_scope_is_opt_in() -> None:
    q = "open the board"
    off = {x.token: x for x in Grounder(TEXTS + ["board"], wiktionary=_wk()).terms(q)}["board"]
    on = {
        x.token: x
        for x in Grounder(TEXTS + ["board"], wiktionary=_wk(), wiktionary_known=True).terms(q)
    }["board"]
    assert off.kind == on.kind == "known"
    assert "dashboard" not in off.alts and "dashboard" in on.alts


def test_config_wires_wiktionary_and_defaults_off() -> None:
    assert Copilot().wiktionary is None
    bot = Copilot(config=replace(CopilotConfig(), use_wiktionary_backoff=True, wiktionary_min_score=2))
    assert bot.wiktionary is not None and bot.wiktionary.min_score == 2
    assert bot.grounder.wiktionary is bot.wiktionary and bot.retriever.wiktionary is bot.wiktionary
