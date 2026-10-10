"""Passage-level answer support: does this *passage* answer this *question*?

PR #16 ended on: lexical substitution looks exhausted, the next step is a
model that reads the whole query against the whole passage. This is the
small, offline version of that idea: a logistic-regression pair classifier
trained on outside (question title, answer) pairs from Stack Exchange, whose
features compare the whole question with the whole passage instead of
looking a word up in a list.

Features of a (question words Q, passage words P) pair, each query word
weighted by its IDF ``w_q`` (Stack Exchange answers at training time, the
corpus at run time):

``lex``       sum of ``w_q`` over q in P / sum of ``w_q`` (lexical coverage)
``soft``      the same with credit ``s_q = max_{a in P} cos(q, a)`` (clipped at
              ``SIM_FLOOR``, 1 for an exact match) for words P lacks,
              ``domain_vectors`` cosines
``weakest``   the lowest ``s_q`` among missing words (1 if none is missing)
``missing``   fraction of query words P lacks
``centroid``  cosine of the IDF-weighted mean vectors of Q and P

Training (``build_training_pairs``): train-split questions only. Each
question gives its own answer as a positive and two negatives: the answer of
another question (same site) with the highest lexical coverage among
``HARD_POOL`` random ones (a *hard* negative that shares words) and one
random answer. ``LogisticRegression`` (L2, C=1, balanced classes) on
standardised features; nothing here looks at this repo's corpus or eval.

Out-of-sample check (``evaluate``): hash-held-out test questions. ROC AUC of
own answer vs the two kinds of negative, and the rank of the own answer among
``RANK_POOL`` candidates, for lexical coverage alone, the classifier without
the vector features, and the full classifier.

At run time the classifier is a *backoff* inside the grounding gate
(``Grounder.passage_support``): it can vouch for a few missing plain query
words when the probability that the evidence answers the question is above a
threshold calibrated on clean + dev rows only. Identifiers never go through
it.
"""

from __future__ import annotations

import json
import math
import random
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Callable, Iterable, Mapping, Sequence

import numpy as np

from ops_copilot.domain_vectors import DomainVectors, default_vectors

DATA_DIR = Path(__file__).resolve().parents[2] / "data" / "domainvec"
DEFAULT_MODEL = DATA_DIR / "passage_support.json"
FEATURES: tuple[str, ...] = ("lex", "soft", "weakest", "missing", "centroid")
LEXICAL_FEATURES: tuple[str, ...] = ("lex", "missing")
SIM_FLOOR = 0.0
HARD_POOL = 30
RANK_POOL = 50
SAMPLE_SEED = 17
MAX_TEST_QUERIES = 1000


def idf_from(docs: Iterable[Iterable[str]]) -> dict[str, float]:
    df: dict[str, int] = {}
    n = 0
    for d in docs:
        n += 1
        for w in set(d):
            df[w] = df.get(w, 0) + 1
    return {w: math.log((n - c + 0.5) / (c + 0.5) + 1.0) for w, c in df.items()}


def _mean_vec(dv: DomainVectors, ws: Sequence[str], weight: Callable[[str], float]) -> np.ndarray | None:
    idx = [(dv.index[w], weight(w)) for w in ws if w in dv.index]
    if not idx:
        return None
    v = np.sum([dv.vectors[i] * wt for i, wt in idx], axis=0)
    n = float(np.linalg.norm(v))
    return v / n if n > 0 else None


def pair_features(
    q_words: Sequence[str],
    p_words: Iterable[str],
    weight: Callable[[str], float],
    dv: DomainVectors,
) -> dict[str, float] | None:
    """Feature dict of one pair, plus ``best`` (missing word -> (passage word, cos))."""
    q = list(dict.fromkeys(q_words))
    if not q:
        return None
    pset = set(p_words)
    ws = {w: max(weight(w), 1e-6) for w in q}
    total = sum(ws.values())
    hit = [w for w in q if w in pset]
    missing = [w for w in q if w not in pset]
    plist = [a for a in pset if a in dv.index]
    pmat = dv.vectors[[dv.index[a] for a in plist]] if plist else None
    credit: dict[str, float] = {w: 1.0 for w in hit}
    best: dict[str, tuple[str | None, float]] = {}
    for w in missing:
        v = dv.vector(w)
        if v is None or pmat is None:
            credit[w] = 0.0
            best[w] = (None, 0.0)
            continue
        sims = pmat @ v
        k = int(np.argmax(sims))
        credit[w] = max(float(sims[k]), SIM_FLOOR)
        best[w] = (plist[k], float(sims[k]))
    qv = _mean_vec(dv, q, lambda w: ws[w])
    pv = _mean_vec(dv, plist, weight) if plist else None
    return {
        "lex": sum(ws[w] for w in hit) / total,
        "soft": sum(ws[w] * credit[w] for w in q) / total,
        "weakest": min((credit[w] for w in missing), default=1.0),
        "missing": len(missing) / len(q),
        "centroid": float(qv @ pv) if qv is not None and pv is not None else 0.0,
        "best": best,  # type: ignore[dict-item]
    }


def _row(f: Mapping[str, float], names: Sequence[str]) -> list[float]:
    return [float(f[n]) for n in names]


# ---------------------------------------------------------------------------
# training and out-of-sample evaluation (build time; needs the raw pages)


def build_training_pairs(
    pairs: Sequence[dict], idf: Mapping[str, float], seed: int = SAMPLE_SEED
) -> list[tuple[list[str], list[str], int, str]]:
    """(q, passage, label, kind) with one positive and two negatives per question."""
    rng = random.Random(seed)
    by_q: dict[tuple[str, int], dict] = {}
    for p in pairs:
        by_q.setdefault((p["site"], p["qid"]), p)  # first (accepted / top) answer
    items = list(by_q.values())
    by_site: dict[str, list[dict]] = {}
    for p in items:
        by_site.setdefault(p["site"], []).append(p)
    out: list[tuple[list[str], list[str], int, str]] = []

    def lex(q, a):
        s = set(a)
        tot = sum(idf.get(w, 1.0) for w in q) or 1.0
        return sum(idf.get(w, 1.0) for w in q if w in s) / tot

    for p in items:
        site = by_site[p["site"]]
        if len(site) < 3:
            continue
        out.append((p["q"], p["a"], 1, "own"))
        pool = [o for o in rng.sample(site, min(HARD_POOL + 1, len(site))) if o is not p][:HARD_POOL]
        hard = max(pool, key=lambda o: (lex(p["q"], o["a"]), -o["aid"]))
        out.append((p["q"], hard["a"], 0, "hard"))
        rand = rng.choice([o for o in site if o is not p])
        out.append((p["q"], rand["a"], 0, "random"))
    return out


@dataclass
class PairClassifier:
    names: tuple[str, ...]
    mean: np.ndarray
    scale: np.ndarray
    coef: np.ndarray
    intercept: float

    def logit(self, f: Mapping[str, float]) -> float:
        x = (np.array(_row(f, self.names)) - self.mean) / self.scale
        return float(x @ self.coef + self.intercept)

    def prob(self, f: Mapping[str, float]) -> float:
        return 1.0 / (1.0 + math.exp(-self.logit(f)))

    def as_dict(self) -> dict:
        return {
            "features": list(self.names),
            "mean": [round(float(x), 6) for x in self.mean],
            "scale": [round(float(x), 6) for x in self.scale],
            "coef": [round(float(x), 6) for x in self.coef],
            "intercept": round(float(self.intercept), 6),
        }

    @classmethod
    def from_dict(cls, d: Mapping) -> "PairClassifier":
        return cls(
            tuple(d["features"]),
            np.array(d["mean"], dtype=float),
            np.array(d["scale"], dtype=float),
            np.array(d["coef"], dtype=float),
            float(d["intercept"]),
        )


def fit_classifier(feats: Sequence[Mapping[str, float]], labels: Sequence[int], names: Sequence[str]) -> PairClassifier:
    from sklearn.linear_model import LogisticRegression

    x = np.array([_row(f, names) for f in feats])
    y = np.array(labels)
    mean = x.mean(axis=0)
    scale = np.where(x.std(axis=0) > 0, x.std(axis=0), 1.0)
    lr = LogisticRegression(C=1.0, class_weight="balanced", max_iter=1000)
    lr.fit((x - mean) / scale, y)
    return PairClassifier(tuple(names), mean, scale, lr.coef_[0], float(lr.intercept_[0]))


def _auc(pos: Sequence[float], neg: Sequence[float]) -> float:
    from sklearn.metrics import roc_auc_score

    return float(roc_auc_score([1] * len(pos) + [0] * len(neg), list(pos) + list(neg)))


def evaluate(
    test_pairs: Sequence[dict],
    models: Mapping[str, PairClassifier | None],
    idf: Mapping[str, float],
    dv: DomainVectors,
    seed: int = SAMPLE_SEED,
) -> dict:
    """AUC (own vs hard / random) and rank of the own answer among ``RANK_POOL``."""
    weight = lambda w: idf.get(w, 1.0)  # noqa: E731
    triples = build_training_pairs(test_pairs, idf, seed)
    feats = [pair_features(q, a, weight, dv) for q, a, _, _ in triples]
    kinds = [k for _, _, _, k in triples]

    def score(name: str, f) -> float:
        m = models[name]
        return f["lex"] if m is None else m.prob(f)

    auc: dict[str, dict[str, float]] = {}
    for name in models:
        s = [score(name, f) for f in feats]
        pos = [x for x, k in zip(s, kinds) if k == "own"]
        auc[name] = {
            "vs_hard": _auc(pos, [x for x, k in zip(s, kinds) if k == "hard"]),
            "vs_random": _auc(pos, [x for x, k in zip(s, kinds) if k == "random"]),
        }
    # ranking: own answer among RANK_POOL - 1 random others
    rng = random.Random(seed + 1)
    firsts: dict[tuple[str, int], dict] = {}
    for p in test_pairs:
        firsts.setdefault((p["site"], p["qid"]), p)
    items = list(firsts.values())
    queries = items if len(items) <= MAX_TEST_QUERIES else rng.sample(items, MAX_TEST_QUERIES)
    ranks: dict[str, list[int]] = {n: [] for n in models}
    ranks_missing: dict[str, list[int]] = {n: [] for n in models}
    for p in queries:
        others = rng.sample([o for o in items if o is not p], RANK_POOL - 1)
        cands = [p, *others]
        fs = [pair_features(p["q"], c["a"], weight, dv) for c in cands]
        all_missing = not (set(p["q"]) & set(p["a"]))
        for name in models:
            s = np.array([score(name, f) for f in fs])
            r = 1 + int(np.sum(s[1:] > s[0])) + int(np.sum(s[1:] == s[0])) // 2
            ranks[name].append(r)
            if all_missing:
                ranks_missing[name].append(r)

    def summ(rs: list[int]) -> dict:
        if not rs:
            return {"n": 0, "p_at_1": 0.0, "mrr": 0.0}
        a = np.array(rs)
        return {"n": len(rs), "p_at_1": float(np.mean(a == 1)), "mrr": float(np.mean(1.0 / a))}

    return {
        "n_test_questions": len(items),
        "n_rank_queries": len(queries),
        "rank_pool": RANK_POOL,
        "auc": auc,
        "rank": {n: summ(r) for n, r in ranks.items()},
        "rank_no_shared_word": {n: summ(r) for n, r in ranks_missing.items()},
    }


# ---------------------------------------------------------------------------
# run time


@dataclass
class PassageVerdict:
    prob: float
    features: dict
    best: dict  # missing word -> (passage word, cosine)


class PassageSupportModel:
    """Committed classifier + domain vectors; scores (query words, passage words)."""

    def __init__(
        self,
        classifier: PairClassifier,
        vectors: DomainVectors | None = None,
        *,
        threshold: float = 0.5,
        meta: dict | None = None,
    ) -> None:
        self.classifier = classifier
        self.vectors = vectors or default_vectors()
        self.threshold = float(threshold)
        self.meta = meta or {}

    @classmethod
    def load(cls, path: str | Path | None = None, **kw) -> "PassageSupportModel":
        raw = _load_model(str(path or DEFAULT_MODEL))
        return cls(PairClassifier.from_dict(raw["classifier"]), meta=raw["meta"], **kw)

    def verdict(
        self, q_words: Sequence[str], p_words: Iterable[str], weight: Callable[[str], float]
    ) -> PassageVerdict | None:
        f = pair_features(q_words, p_words, weight, self.vectors)
        if f is None:
            return None
        best = f.pop("best")
        return PassageVerdict(self.classifier.prob(f), f, best)


@lru_cache(maxsize=2)
def _load_model(path: str) -> dict:
    return json.loads(Path(path).read_text())
