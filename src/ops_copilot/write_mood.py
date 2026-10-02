"""Imperative vs informational mood detection for the write gate.

The question the write gate must answer first is not *which* action but
whether the user is giving an instruction at all. "How do I restart
checkout-api?" and "checkout-api restarts every night" mention the action;
"restart checkout-api", "can you restart checkout-api?" and "I need you to
restart checkout-api" ask for it.

``analyze_mood`` works per clause (the raw query is split on ``, ; : ! ?``
before normalizing, so "Payments is down, page the on-call" has an
instruction in its second clause):

1. **Informational cue anywhere** (the PR #12 read cues, extended): a wh-word
   with an auxiliary, "steps/procedure/runbook to", first-person modality
   ("can I", "should we", "do we"), "is it safe to", "what if". Any cue makes
   the whole query a read. A missed write is the safe failure here.
2. **Politeness clauses** made only of filler/stopwords ("hey team", "when
   you get a chance", "if you can") are dropped.
3. **Condition clauses** ("if latency spikes", "once the deploy finishes")
   mark any later instruction CONDITIONAL: the classifier asks instead of
   proposing.
4. **Clause head**: leading politeness ("please", "go ahead and") and request
   frames ("can/could/would/will you", "I need/want you to", "let's") are
   skipped; the next token is the clause head. A head that is an auxiliary
   or wh-word is a question (INFORMATIONAL); a subject (pronoun, identifier,
   or a word followed by a copula: "payments is down") is DECLARATIVE; a read verb ("show", "tell",
   "check") is INFORMATIONAL; a negation before it ("don't", "never") is
   NEGATED; otherwise the clause is IMPERATIVE (bare) or REQUEST (framed).
   "can" directly followed by a write verb ("Can restart you X?", a
   word-order perturbation) is REQUEST with lower confidence.

The mood says nothing about which action: ``write_intent`` checks the head
against the ontology lexicons (or the prototype backoff).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum

from ops_copilot.lexicon import AUXILIARIES, WH_WORDS, fix_interrogative_typos
from ops_copilot.text import NON_SALIENT, is_identifier, normalize_text
from ops_copilot.write_ontology import READ_VERBS, action_verbs


class Mood(str, Enum):
    IMPERATIVE = "imperative"
    REQUEST = "request"
    INFORMATIONAL = "informational"
    DECLARATIVE = "declarative"
    NEGATED = "negated"
    CONDITIONAL = "conditional"
    EMPTY = "empty"


INSTRUCTION_MOODS = frozenset({Mood.IMPERATIVE, Mood.REQUEST})

# PR #12 read cues (position-independent), plus first-person modality,
# safety/permission questions and hypotheticals.
INFORMATIONAL_CUES = re.compile(
    r"\b(?:"
    r"how(?:\s+\w+){0,2}?\s+(?:do|does|did|can|could|should|would|to)"
    r"|what\s+(?:is|are|does|was|were|happens|if|would)"
    r"|where\s+(?:is|are|do|does)"
    r"|who\s+(?:is|are|does|can|should|may|gets|owns)"
    r"|when\s+(?:is|does|do|should|was|did|can)"
    r"|why\s+(?:is|does|do|did|was|would)"
    r"|which\s+\w+\s+(?:is|are|does|do|should|can)"
    r"|(?:procedure|process|instructions|runbook|playbook)\s+(?:to|for)"
    r"|(?:can|could|should|may|must|do|did|would)\s+(?:i|we)\b"
    r"|is\s+it\s+(?:safe|ok|okay|possible|allowed|necessary)"
    r"|(?:am|are)\s+(?:i|we)\s+allowed"
    r"|explain|describe"
    r")\b",
    re.IGNORECASE,
)

_CLAUSE_SPLIT = re.compile(r"[,;:!?\n]+|\s+-\s+|\s+but\s+", re.IGNORECASE)
_SKIP = frozenset(
    {
        "please",
        "kindly",
        "pls",
        "plz",
        "just",
        "now",
        "so",
        "ok",
        "okay",
        "hey",
        "hi",
        "hello",
        "team",
        "folks",
        "quick",
        "one",
        "also",
        "then",
        "immediately",
        "asap",
        "urgently",
        "go",
        "ahead",
        "and",
        "actually",
        "right",
        "away",
    }
)
_REQUEST_AUX = frozenset({"can", "could", "would", "will"})
_YOU = frozenset({"you", "u"})
_NEEDS = frozenset({"need", "needs", "want", "wanted", "like"})
_NEGATIONS = frozenset({"dont", "don", "never", "not", "no", "nobody", "avoid"})
_CONDITIONS = frozenset({"if", "unless", "once", "whenever", "after", "before", "until", "when", "in"})
_QUESTION_HEADS = (AUXILIARIES - _REQUEST_AUX) | frozenset({"has", "have", "had", "am"})
# A clause whose head is a subject ("we restart it nightly", "checkout-api
# restarts every night", "payments is down") describes, it does not instruct.
_SUBJECT_HEADS = frozenset(
    {"we", "i", "they", "he", "she", "it", "you", "someone", "everyone", "this", "that", "there"}
)
_COPULA_NEXT = frozenset({"is", "are", "was", "were", "has", "have", "had", "seems", "looks", "keeps"})


@dataclass
class Clause:
    tokens: list[str]
    head: int = -1  # index into tokens of the clause head, -1 = none
    mood: Mood = Mood.EMPTY
    frame: str = ""
    confidence: float = 0.0

    @property
    def head_word(self) -> str:
        return self.tokens[self.head] if 0 <= self.head < len(self.tokens) else ""

    def as_dict(self) -> dict:
        return {
            "text": " ".join(self.tokens),
            "head": self.head_word,
            "mood": self.mood.value,
            "frame": self.frame,
            "confidence": round(self.confidence, 3),
        }


@dataclass
class MoodResult:
    mood: Mood
    cue: str = ""
    clauses: list[Clause] = field(default_factory=list)

    @property
    def instruction_clauses(self) -> list[Clause]:
        return [c for c in self.clauses if c.mood in INSTRUCTION_MOODS]

    def as_dict(self) -> dict:
        return {
            "mood": self.mood.value,
            "cue": self.cue,
            "clauses": [c.as_dict() for c in self.clauses],
        }


def _is_polite(tokens: list[str]) -> bool:
    return all(t in NON_SALIENT or t in _SKIP for t in tokens)


def _analyze_clause(tokens: list[str], write_verbs: frozenset[str]) -> Clause:
    clause = Clause(tokens=tokens)
    i, n = 0, len(tokens)
    frame = "bare"
    negated = False
    conf = 1.0
    while i < n:
        tok = tokens[i]
        nxt = tokens[i + 1] if i + 1 < n else ""
        if tok in _SKIP:
            if tok == "please" and frame == "bare":
                frame = "please"
            i += 1
            continue
        if tok in _NEGATIONS or (tok == "do" and nxt == "not"):
            negated = True
            i += 2 if tok == "do" else 1
            continue
        if tok in _REQUEST_AUX:
            if nxt in _YOU:
                frame = "request"
                i += 2
                continue
            if nxt in write_verbs:
                frame, conf = "request_inverted", 0.9
                i += 1
                continue
            clause.mood, clause.frame, clause.head = Mood.INFORMATIONAL, "question", i
            return clause
        if tok in ("i", "we", "id") and nxt in _NEEDS | {"would"}:
            # "I need you to", "I want you to", "I would like you to", "we need to"
            j = i + 1
            while j < n and tokens[j] in _NEEDS | _YOU | {"would", "to", "like"}:
                j += 1
            frame = "request"
            i = j
            continue
        if tok == "let" and nxt in ("us", "lets", ""):
            frame = "request"
            i += 2
            continue
        if tok == "let":
            frame = "request"
            i += 1
            continue
        break
    if i >= n:
        clause.mood = Mood.EMPTY
        return clause
    head = tokens[i]
    clause.head, clause.frame = i, frame
    if head in _QUESTION_HEADS or head in WH_WORDS:
        clause.mood, clause.frame = Mood.INFORMATIONAL, "question"
    elif head in READ_VERBS:
        clause.mood, clause.frame = Mood.INFORMATIONAL, "read_verb"
    elif head in _SUBJECT_HEADS or is_identifier(head) or tokens[i + 1 : i + 2] and tokens[i + 1] in _COPULA_NEXT:
        clause.mood, clause.frame = Mood.DECLARATIVE, "subject"
    elif negated:
        clause.mood = Mood.NEGATED
    elif frame == "bare":
        clause.mood, clause.confidence = Mood.IMPERATIVE, conf
    else:
        clause.mood, clause.confidence = Mood.REQUEST, conf
    return clause


def analyze_mood(
    query: str,
    *,
    typo_tolerance: bool = True,
    write_verbs: frozenset[str] | None = None,
) -> MoodResult:
    """Clause-level mood of ``query`` (see module docstring)."""
    verbs = write_verbs if write_verbs is not None else action_verbs()
    nq = normalize_text(query or "")
    if typo_tolerance:
        nq = fix_interrogative_typos(nq)
    if not nq:
        return MoodResult(Mood.EMPTY)
    cue = INFORMATIONAL_CUES.search(nq)
    clauses: list[Clause] = []
    conditional = False
    for raw in _CLAUSE_SPLIT.split(query or ""):
        text = normalize_text(raw)
        if typo_tolerance:
            text = fix_interrogative_typos(text)
        toks = text.split()
        if not toks or _is_polite(toks):
            continue
        if toks[0] in _CONDITIONS and not (toks[0] == "in" and toks[1:2] != ["case"]):
            conditional = True
            clauses.append(Clause(tokens=toks, mood=Mood.DECLARATIVE, frame="condition"))
            continue
        clause = _analyze_clause(toks, verbs)
        if conditional and clause.mood in INSTRUCTION_MOODS:
            clause.mood = Mood.CONDITIONAL
        clauses.append(clause)
    if cue:
        return MoodResult(Mood.INFORMATIONAL, cue=cue.group(0), clauses=clauses)
    for wanted in (Mood.IMPERATIVE, Mood.REQUEST, Mood.CONDITIONAL, Mood.NEGATED, Mood.INFORMATIONAL):
        if any(c.mood is wanted for c in clauses):
            return MoodResult(wanted, clauses=clauses)
    return MoodResult(Mood.DECLARATIVE if clauses else Mood.EMPTY, clauses=clauses)
