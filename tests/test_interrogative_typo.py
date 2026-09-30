"""g28-typo: a misspelt wh-word is read from query context, not corpus df."""

from __future__ import annotations

from ops_copilot import Copilot, CopilotConfig
from ops_copilot.lexicon import CorpusVocabulary, fix_interrogative_typos
from ops_copilot.text import NON_SALIENT
from ops_copilot.types import Decision

G28_TYPO = "Wat is the sidecar meah mtls handshake budget?"


def _vocab() -> CorpusVocabulary:
    return CorpusVocabulary([["wait", "sidecar", "mesh"], ["wait"]], extra_words=NON_SALIENT)


def test_df_tie_break_alone_picks_the_corpus_word() -> None:
    # the old behaviour this fixes: stopwords have no df, so 'wait' wins
    assert _vocab().tied_candidates("wat") == ["wait"]


def test_context_turns_wat_is_into_what_is() -> None:
    v = _vocab()
    assert fix_interrogative_typos("wat is the sidecar budget", v) == "what is the sidecar budget"
    assert fix_interrogative_typos("waht does it cost", v) == "what does it cost"
    # without a vocabulary (write gate) the keyboard model alone decides
    assert fix_interrogative_typos("hwo do i drain it") == "how do i drain it"


def test_context_rule_leaves_known_words_and_non_questions_alone() -> None:
    v = _vocab()
    assert fix_interrogative_typos("wait is over", v) == "wait is over"  # known word
    assert fix_interrogative_typos("wat sidecar budget", v) == "wat sidecar budget"  # no auxiliary
    assert fix_interrogative_typos("what is it", v) == "what is it"


def test_grounder_no_longer_demands_wait(copilot: Copilot) -> None:
    tokens = [t.token for t in copilot.grounder.terms(G28_TYPO)]
    assert "wait" not in tokens and "wat" not in tokens
    assert "mesh" in tokens  # the other typo still snaps


def test_g28_typo_row_reaches_the_clean_label(copilot: Copilot) -> None:
    assert copilot.ask(G28_TYPO).decision is Decision.REFUSE_DISAGREE
    assert "wait" not in copilot.retriever.rewrite_query(G28_TYPO).split()


def test_context_rule_is_part_of_typo_tolerance() -> None:
    bot = Copilot(config=CopilotConfig(typo_tolerance=False))
    assert bot.grounder._query_tokens(G28_TYPO)[0] == "wat"
