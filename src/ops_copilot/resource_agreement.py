"""Resource-agreement synonyms: a substitute counts only when several outside resources agree.

Every outside synonym resource tried so far was gated on its own (counter-fitted vectors,
Datamuse means-like, WordNet, Wiktionary, Stack Exchange tag synonyms), and each one that
added held-out rows also opened a trap (Datamuse ``legal -> duty``, Oct 22 / Oct 26). A
single general-English resource cannot tell an ops sense from an everyday one. This
backoff asks a different question: is the pair proposed by at least ``min_votes`` of the
five resources? The idea is that a wrong sense is usually an artefact of one resource,
while a real synonym tends to be listed by several.

Caveat, stated up front: the resources are not fully independent. The counter-fitted
vectors were fitted to PPDB and WordNet constraints, and Datamuse draws on WordNet too,
so ``wordvec`` + ``wordnet`` agreeing is weaker evidence than two unrelated sources.

Per-resource gates are fixed a priori and loose on purpose (agreement is the filter):
counter-fitted cosine >= ``WORDVEC_MIN`` (the committed table's floor is 0.50), Datamuse
rank <= ``DATAMUSE_MAX_RANK``, WordNet path <= 1 (synonym or direct hyper/hyponym),
Wiktionary score >= 1 (synonym, pointer or gloss head), tag synonyms on any site.

Scopes (as in ``WordNetNounSense``): ``known`` expands corpus words only (grounding alts
for a known word the evidence lacks); ``lone`` also maps an unknown word when it is the
query's only unknown content word; ``all`` maps every unknown word. Returning nothing is
the safe answer: the word stays a high-weight unknown and grounding refuses as before.

Plugs into the grounder's noun read-path slot (``ChainedNounSense``). No eval word was
used to build or filter any of the five resources; none of them is edited here.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from typing import Callable

from ops_copilot.semantic import Neighbour
from ops_copilot.text import fold_token, is_identifier

SOURCES = ("wordvec", "datamuse", "wordnet", "wiktionary", "tagsyn")
SCOPES = ("known", "lone", "all")
WORDVEC_MIN = 0.60
DATAMUSE_MAX_RANK = 50
WORDNET_MAX_PATH = 1
MIN_WORD_LEN = 3


def default_proposers(corpus_texts: list[str]) -> dict[str, Callable[[str], frozenset[str]]]:
    """One candidate-set function per resource over the committed tables (loose gates)."""
    from ops_copilot.datamuse_senses import load_table as load_datamuse
    from ops_copilot.tag_synonyms import TagSynonymBackoff, tag_synonym_sites
    from ops_copilot.wiktionary_senses import WiktionarySenseBackoff
    from ops_copilot.word_vectors import corpus_words
    from ops_copilot.word_vectors import load_table as load_wordvec
    from ops_copilot.wordnet_senses import load_table as load_wordnet

    words = frozenset(corpus_words(corpus_texts))
    wv, dm, wn = load_wordvec(), load_datamuse(), load_wordnet()
    wk = WiktionarySenseBackoff(corpus_texts, min_score=1, max_neighbours=10_000)
    ts = TagSynonymBackoff(corpus_texts, sites=tag_synonym_sites("all"), min_sites=1, max_neighbours=10_000)

    def rows(table_get, tok):
        got = table_get(tok)
        if not got and fold_token(tok) != tok:
            got = table_get(fold_token(tok))
        return got or ()

    return {
        "wordvec": lambda t: frozenset(w for w, s in rows(wv.get, t) if s >= WORDVEC_MIN and w in words),
        "datamuse": lambda t: frozenset(
            r[0] for r in rows(dm.neighbours.get, t) if r[1] <= DATAMUSE_MAX_RANK and r[0] in words),
        "wordnet": lambda t: frozenset(
            r[0] for r in rows(wn.neighbours.get, t) if r[2] <= WORDNET_MAX_PATH and r[0] in words),
        "wiktionary": lambda t: frozenset(n.word for n in wk.neighbours(t)),
        "tagsyn": lambda t: frozenset(n.word for n in ts.neighbours(t)),
    }


@dataclass
class AgreementSense:
    """Corpus words that at least ``min_votes`` resources propose for a query word."""

    corpus_words: frozenset[str]
    proposers: dict[str, Callable[[str], frozenset[str]]]
    min_votes: int = 2
    scope: str = "known"
    max_neighbours: int = 1
    suspend_unknown: bool = False
    _cache: dict[str, tuple[Neighbour, ...]] = field(default_factory=dict, repr=False)

    term_kind = "resource_agreement"

    def __post_init__(self) -> None:
        if self.scope not in SCOPES:
            raise ValueError(f"scope must be one of {SCOPES}, got {self.scope!r}")
        if not 1 <= self.min_votes <= len(self.proposers):
            raise ValueError(f"min_votes must be in [1, {len(self.proposers)}]")
        if self.max_neighbours < 1:
            raise ValueError("max_neighbours must be >= 1")

    @classmethod
    def from_corpus(cls, corpus_texts: list[str], **kw) -> "AgreementSense":
        from ops_copilot.word_vectors import corpus_words

        return cls(frozenset(corpus_words(corpus_texts)), default_proposers(corpus_texts), **kw)

    @property
    def lone_unknown(self) -> bool:
        return self.scope == "lone"

    def set_suspend_unknown(self, value: bool) -> None:
        self.suspend_unknown = bool(value)

    @staticmethod
    def lookupable(token: str) -> bool:
        return token.isalpha() and not is_identifier(token) and len(token) >= MIN_WORD_LEN

    def votes(self, token: str) -> Counter:
        """Candidate corpus word -> number of resources proposing it (``token`` excluded)."""
        tok = token.lower()
        same = {tok, fold_token(tok)}
        out: Counter = Counter()
        for name in self.proposers:
            for w in self.proposers[name](tok):
                if w not in same and fold_token(w) not in same:
                    out[w] += 1
        return out

    def neighbours(self, token: str) -> tuple[Neighbour, ...]:
        if not self.lookupable(token):
            return ()
        tok = token.lower()
        known = tok in self.corpus_words or fold_token(tok) in self.corpus_words
        if not known and (self.scope == "known" or self.suspend_unknown):
            return ()
        if tok in self._cache:
            return self._cache[tok]
        ranked = sorted(((-n, w) for w, n in self.votes(tok).items() if n >= self.min_votes))
        out = tuple(Neighbour(w, float(-n), "resource_agreement") for n, w in ranked[: self.max_neighbours])
        self._cache[tok] = out
        return out
