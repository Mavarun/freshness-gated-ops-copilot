"""Extractive answer builder (no external LLM) and refusal templates."""

from __future__ import annotations

from ops_copilot.text import content_tokens, split_sentences
from ops_copilot.types import Chunk, Decision

REFUSAL_TEMPLATES = {
    Decision.REFUSE_STALE: (
        "REFUSED: retrieved evidence is older than the freshness SLA. "
        "I will not answer from stale ops data."
    ),
    Decision.REFUSE_UNGROUNDED: (
        "REFUSED: retrieved evidence does not lexically support the query. "
        "I will not invent an ungrounded answer."
    ),
    Decision.REFUSE_NO_EVIDENCE: (
        "REFUSED: no retrieved evidence cleared the score floor for this query."
    ),
}


def _sentence_score(query_tokens: set[str], sentence: str) -> float:
    sent_tokens = set(content_tokens(sentence))
    if not query_tokens or not sent_tokens:
        return 0.0
    return len(query_tokens & sent_tokens) / len(query_tokens)


def extractive_answer(
    query: str,
    evidence: list[Chunk],
    *,
    max_sentences: int = 2,
) -> str:
    """Pull the best query-overlapping sentences from fresh evidence."""
    q_toks = set(content_tokens(query))
    candidates: list[tuple] = []
    for chunk in evidence:
        for sent in split_sentences(chunk.text):
            words = sent.split()
            if len(words) < 6:
                continue
            score = _sentence_score(q_toks, sent)
            if score <= 0:
                continue
            lead = 1 if chunk.chunk_id.endswith("::p0") else 0
            candidates.append((score, lead, -len(candidates), sent.strip(), chunk.doc_id))
    candidates.sort(reverse=True)
    picked: list[str] = []
    cited: list[str] = []
    seen: set[str] = set()
    for score, _lead, _, sent, doc_id in candidates:
        key = sent.lower()
        if key in seen:
            continue
        seen.add(key)
        picked.append(sent)
        cited.append(doc_id)
        if len(picked) >= max_sentences:
            break
    if not picked:
        return ""
    cite = ", ".join(dict.fromkeys(cited))
    return f"{' '.join(picked)} [sources: {cite}]"


def render_refusal(decision: Decision, reason: str) -> str:
    template = REFUSAL_TEMPLATES.get(decision)
    if template is None:
        return reason
    return f"{template} Reason: {reason}"
