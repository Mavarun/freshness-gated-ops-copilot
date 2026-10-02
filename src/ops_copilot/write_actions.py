"""Schemas and offline heuristics for proposed *write* actions.

Read-path ANSWER is fine. Imperative writes (restart, page oncall, patch config)
must be structured proposals — never auto-executed. Keyword/heuristic detection
is intentional for the offline golden set (no paid LLM).

Detection runs on ``text.normalize_text(query)`` so case, curly quotes, and
trailing punctuation never decide whether a write is proposed. With typo
tolerance on, words of 5+ characters one keyboard slip from a write keyword
(``rrstart``, ``pathc``, ``onclal``) are read as that keyword; inflections
(``restarts``, ``patched``) are left alone so descriptions do not become writes.
A misspelt wh-word before an auxiliary ("hwo do I restart X", "wat is") is
read as the wh-word first, so a typo cannot turn a how-to read into a write.
With synonyms on, the restart verbs come from the corpus-side equivalence
group (``synonyms.restart_verbs``; only ``restart`` itself since the held-out
split removed reboot / bounce / recycle).
"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from typing import Any

from ops_copilot.lexicon import fix_interrogative_typos, is_keyboard_typo
from ops_copilot.synonyms import restart_verbs
from ops_copilot.text import is_identifier, normalize_text
from ops_copilot.write_ontology import WriteActionType  # noqa: F401  (re-export)


# How-to / definition reads must not trip the write gate. Matched anywhere in
# the normalized query, not only at the start: "Quick question: how do I
# restart X?" and "I was wondering, what is the procedure to restart X" are
# reads. "how" may sit up to two words before its auxiliary ("how I do",
# "how would we"). Missing a write here is the safe failure: the query falls
# through to the evidence gates and is answered or refused, never executed.
_READ_CUES = re.compile(
    r"\b(?:"
    r"how(?:\s+\w+){0,2}?\s+(?:do|does|did|can|could|should|would|to)"
    r"|what\s+(?:is|are|does|was|were)"
    r"|where\s+(?:is|are|do|does)"
    r"|who\s+(?:is|are|does)"
    r"|when\s+(?:is|does|do|should)"
    r"|why\s+(?:is|does|do|did)"
    r"|(?:steps|procedure|process|instructions|runbook)\s+(?:to|for)"
    r"|explain|describe"
    r")\b",
    re.IGNORECASE,
)

def _restart_re(verbs: tuple[str, ...]) -> re.Pattern[str]:
    return re.compile(
        r"\b(?:please\s+|go\s+ahead\s+and\s+|can\s+you\s+|could\s+you\s+)?"
        rf"(?:{'|'.join(verbs)})\s+(?:the\s+)?(?P<target>[\w.-]+)",
        re.IGNORECASE,
    )


_RESTART = _restart_re(("restart",))
_RESTART_SYN = _restart_re(restart_verbs())
# Position-independent: the cue may sit anywhere in the query and anything may
# follow it ("page the oncall the for outage payments" after word-order
# noise). The target is read separately from the first "for ..." after it.
# Before, the pattern was anchored to the end of the query, so a shuffled
# or trailing clause silently dropped the write (g42-word_order).
_PAGE = re.compile(r"\bpage\s+(?:the\s+)?on[- ]?call\b", re.IGNORECASE)
_PAGE_TARGET = re.compile(
    r"\bfor\s+(?:the\s+)?(?P<target>[\w.-]+(?:\s+[\w.-]+)*?)(?:\s+now)?\s*$",
    re.IGNORECASE,
)
_PATCH = re.compile(
    r"\b(?:please\s+|can\s+you\s+|could\s+you\s+)?"
    r"patch\s+(?:the\s+)?(?P<target>[\w./:-]+)(?:\s+config)?\b"
    r"(?:\s+(?:to|with)\s+(?P<value>[\w.-]+))?",
    re.IGNORECASE,
)


# Keywords the regexes below key on; typo snapping targets only these.
WRITE_KEYWORDS: tuple[str, ...] = ("restart", "patch", "oncall", "on-call", "config")


def _snap_write_keywords(text: str) -> str:
    out: list[str] = []
    for word in text.split():
        if len(word) >= 5 and word.isalpha() and not is_identifier(word):
            for kw in WRITE_KEYWORDS:
                if word == kw or word.startswith(kw) or kw.startswith(word):
                    break
                if is_keyboard_typo(word, kw):
                    word = kw
                    break
        out.append(word)
    return " ".join(out)


@dataclass
class ProposedWrite:
    """Structured write the agent wants to perform — pending until HITL approve."""

    action_type: WriteActionType
    target: str
    payload: dict[str, Any] = field(default_factory=dict)
    evidence_ids: list[str] = field(default_factory=list)
    query: str = ""

    def as_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["action_type"] = self.action_type.value
        return d


def detect_write_intent(
    query: str,
    *,
    typo_tolerance: bool = True,
    synonyms: bool = True,
) -> ProposedWrite | None:
    """Return a ProposedWrite when ``query`` looks like an imperative write.

    Returns ``None`` for read-path questions (including how-to restart docs).
    """
    q = (query or "").strip()
    nq = normalize_text(q)
    if typo_tolerance:
        nq = fix_interrogative_typos(nq)  # "hwo do I restart X" is still a read
    if not nq or _READ_CUES.search(nq):
        return None
    if typo_tolerance:
        nq = _snap_write_keywords(nq)

    m = (_RESTART_SYN if synonyms else _RESTART).search(nq)
    if m:
        target = m.group("target").strip("-. ")
        return ProposedWrite(
            action_type=WriteActionType.RESTART_SERVICE,
            target=target,
            payload={"service": target, "graceful": True},
            query=q,
        )

    m = _PAGE.search(nq)
    if m:
        t = _PAGE_TARGET.search(nq, m.end())
        raw = (t.group("target") if t else "primary").strip("-. ")
        target = raw or "primary"
        return ProposedWrite(
            action_type=WriteActionType.PAGE_ONCALL,
            target=target,
            payload={"severity": "critical", "reason": q},
            query=q,
        )

    m = _PATCH.search(nq)
    if m:
        target = m.group("target").strip("-. ")
        value = m.group("value")
        payload: dict[str, Any] = {"config_key": target}
        if value:
            payload["value"] = value
        return ProposedWrite(
            action_type=WriteActionType.PATCH_CONFIG,
            target=target,
            payload=payload,
            query=q,
        )

    return None
