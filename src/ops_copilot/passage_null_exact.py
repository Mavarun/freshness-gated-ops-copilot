"""Exact sample distribution of the shipped null test (report-only, 2026-10-27).

The 2026-10-26 sweep ran 20 seeds and found the shipped "0 of 36 traps" result
holds for seed 42 only. Twenty seeds give a coarse picture (each trap's open
rate to within about +/- 0.2) and say nothing about *why*. This module removes
the seed from the question.

1. **Decision trees.** For each row the shipped default (seed 42, sticky,
   q = 0.30) is re-run with every null-test call *forced* to pass or veto, and
   the forced outcomes are enumerated depth-first. Each node stores the
   call's (query, word, passage) and, for every word of the 5,067-word control
   pool, whether that word scores strictly below the real word on that passage
   (``below``; closed form from ``passage_support.substitution_probs``, with the
   exact loop re-run for any word within ``NULL_TIE_EPS`` of the real score,
   so the comparison is the shipped one bit for bit). Leaves hold the final
   decision. Rows that never reach the null test are a single leaf.
2. **Any control sample, exactly.** A sample S of k pool words decides each
   call by ``mean(below[S]) >= q``; walking the tree gives the row's decision
   for that S. One S is shared by every row (as one seed is in a real run), so
   per-sample counts such as "traps opened" keep the correlation between rows.
   ``evaluate_sample`` reproduces the recorded decisions of seeds 1-20 and 42
   (tested), which validates the trees.
3. **Seed-free summaries.** ``sample_distribution`` draws ``n_samples``
   uniform k-subsets (default 10,000; Monte Carlo SE <= 0.005 on any rate) and
   reports, per row, P(open) / P(correct), and the distribution of the number
   of traps opened. ``pool_decision`` walks the same tree with the whole-pool
   percentile, which is what ``passage_support_null_pool`` does at run time.

Rows: the 171 calibration rows and the 36 (spent) attribute traps, the rows the
seed sweep already used. No unseen row is scored. Nothing here changes a config.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

import ops_copilot.grounding as G
from ops_copilot.config import CopilotConfig
from ops_copilot.passage_support import NULL_TIE_EPS, control_pool, control_words, substitution_probs
from ops_copilot.pipeline import Copilot
from ops_copilot.synonym_dev4 import OPENING

N_SAMPLES = 10_000
SAMPLE_RNG = 20261027
MAX_CALLS = 8


@dataclass
class Node:
    """A null-test call (``below`` set) or a leaf (``decision`` set)."""

    decision: str | None = None
    query: str = ""
    word: str = ""
    credited: str = ""  # passage word the classifier credits for ``word`` on this call
    below: np.ndarray | None = None
    passed: "Node | None" = None
    vetoed: "Node | None" = None


class _Forcer:
    """Replaces the grounder's null test: records each call, returns a forced outcome."""

    def __init__(self, pool: tuple[str, ...]):
        self.pool = pool
        self.pattern: list[bool] = []
        self.calls: list[tuple[str, np.ndarray]] = []

    def __call__(self, model, q_words, word, p_words, weight, controls):
        p_list = list(p_words)
        i = len(self.calls)
        real = model.verdict(q_words, p_list, weight)
        if real is None:
            below = np.zeros(len(self.pool), dtype=bool)
        else:
            probs = substitution_probs(model, q_words, word, p_list, weight, self.pool)
            below = np.nan_to_num(probs, nan=np.inf) < real.prob
            near = np.flatnonzero(np.abs(probs - real.prob) <= NULL_TIE_EPS)
            for j in near:  # settle near-ties with the exact shipped comparison
                v = model.verdict([self.pool[j] if w == word else w for w in q_words], p_list, weight)
                below[j] = v is not None and v.prob < real.prob
        cred = (real.best.get(word, (None, 0.0))[0] or "") if real is not None else ""
        self.calls.append((word, below, cred))
        ok = self.pattern[i] if i < len(self.pattern) else True
        return 1.0 if ok else 0.0


def shipped_config() -> CopilotConfig:
    return CopilotConfig()


def build_trees(rows: list[dict], cfg: CopilotConfig | None = None) -> tuple[dict[str, Node], tuple[str, ...]]:
    """Row id -> decision tree under ``cfg`` (default: shipped), plus the control pool."""
    cfg = cfg or shipped_config()
    bot = Copilot(config=cfg)
    g = bot.grounder
    pool = control_pool(g.passage_support.vectors, _exclude(g))
    forcer = _Forcer(pool)
    orig = G.null_percentile
    G.null_percentile = forcer
    try:
        def run(query: str, pattern: list[bool]) -> tuple[str, list]:
            g._null_vetoed.clear()
            forcer.pattern, forcer.calls = list(pattern), []
            dec = bot.ask(query).decision.value
            return dec, list(forcer.calls)

        def explore(query: str, pattern: list[bool]) -> Node:
            dec, calls = run(query, pattern)
            if len(calls) <= len(pattern) or len(pattern) >= MAX_CALLS:
                return Node(decision=dec)
            word, below, cred = calls[len(pattern)]
            return Node(query=query, word=word, credited=cred, below=below,
                        passed=explore(query, pattern + [True]), vetoed=explore(query, pattern + [False]))

        trees = {r["id"]: explore(r["query"], []) for r in rows}
    finally:
        G.null_percentile = orig
        g._null_vetoed.clear()
    return trees, pool


def _exclude(g) -> set[str]:
    from ops_copilot.corpus import Corpus
    from ops_copilot.qa_translation import words as qa_words

    texts = [f"{c.title} {c.text}" for c in Corpus().chunks]
    return {w for t in texts for w in qa_words(t)} | set(g.idf)


def walk(node: Node, passes) -> str:
    """Follow the tree; ``passes(node) -> bool`` decides each call."""
    while node.decision is None:
        node = node.passed if passes(node) else node.vetoed
    return node.decision


def depth(node: Node) -> int:
    """Longest chain of null-test calls in the tree (0 for a row that never reaches it)."""
    return 0 if node.decision is not None else 1 + max(depth(node.passed), depth(node.vetoed))


def evaluate_sample(trees: dict[str, Node], idx: np.ndarray, q: float = 0.30) -> dict[str, str]:
    """Decisions for one control sample (pool indices ``idx``)."""
    return {rid: walk(t, lambda n: float(np.mean(n.below[idx])) >= q) for rid, t in trees.items()}


def pool_decision(trees: dict[str, Node], q: float) -> dict[str, str]:
    """Decisions when every call uses the whole-pool percentile (seed-free mode)."""
    return {rid: walk(t, lambda n: float(np.mean(n.below)) >= q) for rid, t in trees.items()}


def seed_indices(pool: tuple[str, ...], seed: int, k: int = 100) -> np.ndarray:
    """Pool indices of the shipped ``control_words`` sample for ``seed``.

    ``control_words`` samples from the same sorted pool, so excluding every
    vector word outside ``pool`` reproduces it exactly.
    """
    from ops_copilot.domain_vectors import default_vectors

    dv = default_vectors()
    pos = {w: i for i, w in enumerate(pool)}
    words = control_words(dv, set(dv.index) - set(pool), k=k, seed=seed)
    return np.array([pos[w] for w in words])


def sample_distribution(
    trees: dict[str, Node], rows: list[dict], traps: list[dict], n_pool: int, k: int = 100,
    q: float = 0.30, n_samples: int = N_SAMPLES, rng_seed: int = SAMPLE_RNG,
) -> dict:
    """Seed-free summary of the shipped test over ``n_samples`` uniform k-subsets of the pool.

    ``rows`` are scored for correctness (exact expected decision), ``traps``
    for opening (ANSWER / PROPOSE_WRITE). One subset is shared by all rows.
    """
    rng = np.random.default_rng(rng_seed)
    want = {r["id"]: r["expect_decision"] for r in rows}
    must_refuse = {rid for rid, e in want.items() if e not in OPENING}
    trap_ids = {r["id"] for r in traps}
    live = {rid: t for rid, t in trees.items() if t.decision is None}
    fixed = {rid: t.decision for rid, t in trees.items() if t.decision is not None}
    f_correct = sum(fixed[r] == want[r] for r in fixed if r in want)
    f_traps = sum(fixed[r] in OPENING for r in fixed if r in trap_ids)
    f_mr = sum(fixed[r] in OPENING for r in fixed if r in must_refuse)
    opens = dict.fromkeys(live, 0)
    hits = dict.fromkeys(live, 0)
    n_traps_open = np.zeros(n_samples, dtype=int)
    n_mr_open = np.zeros(n_samples, dtype=int)
    n_correct = np.zeros(n_samples, dtype=int)
    for s in range(n_samples):
        idx = rng.choice(n_pool, size=k, replace=False)
        t_open, mr_open, ok = f_traps, f_mr, f_correct
        for rid, d in evaluate_sample(live, idx, q).items():
            o = d in OPENING
            opens[rid] += o
            if rid in trap_ids:
                t_open += o
            else:
                c = d == want[rid]
                hits[rid] += c
                ok += c
                mr_open += o and rid in must_refuse
        n_traps_open[s], n_mr_open[s], n_correct[s] = t_open, mr_open, ok
    vals, counts = np.unique(n_traps_open, return_counts=True)
    return {
        "k": k, "q": q, "n_samples": n_samples, "rng_seed": rng_seed,
        "n_rows": len(rows), "n_traps": len(trap_ids), "n_live": len(live),
        "p_open": {rid: opens[rid] / n_samples for rid in sorted(live) if opens[rid]},
        "p_correct": {rid: hits[rid] / n_samples for rid in sorted(live) if rid in want},
        "traps_opened_hist": {int(v): int(c) for v, c in zip(vals, counts)},
        "p_no_trap_open": float(np.mean(n_traps_open == 0)),
        "p_safe": float(np.mean((n_traps_open == 0) & (n_mr_open == 0))),
        "mean_traps_opened": float(np.mean(n_traps_open)),
        "correct_mean": float(np.mean(n_correct)),
        "correct_p05_p95": [int(np.percentile(n_correct, 5)), int(np.percentile(n_correct, 95))],
    }


