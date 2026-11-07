"""Answer-side null control for the grounding gate: random one-word swaps.

The Nov 6 rewrite slice found that random corpus words swapped for a *missing* term pass
every gate on 43.6% of tries (dev2-dev6). That number was measured on refused queries
only. This module asks the safety question on answers: take a query the shipped default
answers correctly, swap one salient term for a seeded random corpus word, and count how
often the copilot still answers. A random word changes what the question is about
("What is the remaining error budget for max?"), so every such ANSWER is a candidate
false answer.

Each pass is attributed to how the swapped-in word was supported:

- ``passage``: the passage classifier vouched for it (``max<-rate``);
- ``translation`` / ``semantic``: the answer-support table or the embedding rescue;
- ``lexical``: the word itself is in the cited evidence (the swap may still be a fair
  question, e.g. ``canary`` for ``checkout`` when the runbook mentions a canary);
- ``unsupported``: the word is not supported at all and the query passed on the other
  terms' coverage (it was outside the high-IDF key half).

The swap set is fixed by a *reference* copilot (the shipped default): which rows are
eligible, which terms are swapped and which random words are drawn never depend on the
arm being scored, so arms are compared on identical queries.
"""

from __future__ import annotations

import json
import random
from collections import Counter
from dataclasses import asdict, dataclass, field
from pathlib import Path

from ops_copilot.eval import load_golden
from ops_copilot.rewrite_suggest import _eligible, swap_word
from ops_copilot.text import fold_token, tokenize

ROOT = Path(__file__).resolve().parents[2]
MECHANISMS = ("passage", "translation", "semantic", "lexical", "unsupported")


@dataclass(frozen=True)
class Row:
    id: str
    query: str
    expect: str


@dataclass(frozen=True)
class Swap:
    row_id: str
    term: str
    word: str
    query: str


def golden_rows() -> list[Row]:
    return [Row(f"golden-{i:02d}", r["query"], r["expect_decision"]) for i, r in enumerate(load_golden())]


def file_rows(files: tuple[str, ...], root: Path = ROOT) -> list[Row]:
    out: list[Row] = []
    for rel in files:
        for line in (root / rel).read_text(encoding="utf-8").splitlines():
            if line.strip():
                r = json.loads(line)
                out.append(Row(str(r["id"]), r["query"], r["expect_decision"]))
    return out


def corpus_words(bot) -> list[str]:
    """Sorted plain content words of the corpus (the null control's draw pool)."""
    return sorted({t for c in bot.corpus.chunks for t in tokenize(f"{c.title} {c.text}") if _eligible(t, set())})


def build_swaps(rows: list[Row], reference, *, draws: int, seed: int) -> list[Swap]:
    """Seeded swaps on rows the reference copilot answers as expected (ANSWER)."""
    words = corpus_words(reference)
    rng = random.Random(seed)
    out: list[Swap] = []
    for row in rows:
        if row.expect != "ANSWER" or reference.ask(row.query).decision.value != "ANSWER":
            continue
        q_folded = {fold_token(t) for t in tokenize(row.query)}
        pool = [w for w in words if fold_token(w) not in q_folded]
        for term in reference.grounder.terms(row.query):
            for _ in range(draws):
                word = rng.choice(pool)
                q = swap_word(row.query, term.token, word)
                if q is None:
                    break
                out.append(Swap(row.id, term.token, word, q))
    return out


def mechanism(result, word: str) -> str:
    """How the swapped-in ``word`` was supported in an ANSWER ``result``."""
    g = result.grounding
    key = fold_token(word.lower())
    if any(fold_token(p.split("<-", 1)[0]) == key for p in g.passage_rescued or []):
        return "passage"
    if any(fold_token(p.split("<-", 1)[0]) == key for p in g.translation_rescued or []):
        return "translation"
    if any(fold_token(t) == key for t in g.semantic_rescued or []):
        return "semantic"
    if any(fold_token(t) == key for t in g.overlap_tokens or []):
        return "lexical"
    return "unsupported"


@dataclass
class NullScore:
    n_swaps: int = 0
    passed: int = 0
    by_mechanism: dict[str, int] = field(default_factory=lambda: {m: 0 for m in MECHANISMS})
    n_answer_rows: int = 0
    answered: int = 0
    n_refuse_rows: int = 0
    refuse_opened: int = 0
    passes: list[dict] = field(default_factory=list)

    def rates(self) -> dict:
        return {
            "null_pass_rate": self.passed / max(self.n_swaps, 1),
            "answer_rate": self.answered / max(self.n_answer_rows, 1),
            **{f"pass_{m}": self.by_mechanism[m] / max(self.n_swaps, 1) for m in MECHANISMS},
        }

    def as_dict(self) -> dict:
        d = asdict(self)
        d["rates"] = self.rates()
        return d


def score(bot, rows: list[Row], swaps: list[Swap]) -> NullScore:
    """Null passes on ``swaps`` plus the keep/open counts on the original ``rows``."""
    sc = NullScore()
    for row in rows:
        d = bot.ask(row.query).decision.value
        if row.expect == "ANSWER":
            sc.n_answer_rows += 1
            sc.answered += d == "ANSWER"
        elif row.expect.startswith("REFUSE_"):
            sc.n_refuse_rows += 1
            sc.refuse_opened += d == "ANSWER"
    for s in swaps:
        sc.n_swaps += 1
        res = bot.ask(s.query)
        if res.decision.value != "ANSWER":
            continue
        sc.passed += 1
        m = mechanism(res, s.word)
        sc.by_mechanism[m] += 1
        sc.passes.append({"row": s.row_id, "term": s.term, "word": s.word, "query": s.query, "mechanism": m,
                          "passage": list(res.grounding.passage_rescued or [])})
    return sc


def mechanism_counts(passes: list[dict]) -> Counter:
    return Counter(p["mechanism"] for p in passes)
