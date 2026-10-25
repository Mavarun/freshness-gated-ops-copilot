"""Passage-level answer support: does this *passage* answer this *question*?

PR #16 ended on: lexical substitution looks exhausted, the next step is a
model that reads the whole query against the whole passage. This is the
small, offline version of that idea: a logistic-regression pair classifier
trained on outside (question title, answer) pairs from Stack Exchange, whose
features compare the whole question with the whole passage instead of
looking a word up in a list.

Features of a (question words Q, passage words P) pair, each query word
weighted by its IDF ``w_q`` (Stack Exchange answers at training time, the
corpus at run time). The original five:

``lex``       sum of ``w_q`` over q in P / sum of ``w_q`` (lexical coverage)
``soft``      the same with credit ``s_q = max_{a in P} cos(q, a)`` (clipped at
              ``SIM_FLOOR``, 1 for an exact match) for words P lacks,
              ``domain_vectors`` cosines
``weakest``   the lowest ``s_q`` among missing words (1 if none is missing)
``missing``   fraction of query words P lacks
``centroid``  cosine of the IDF-weighted mean vectors of Q and P

Plus six denser offline features (still no model download):

``jaccard``     |Q ∩ P| / |Q ∪ P|
``hit_frac``    unweighted |Q ∩ P| / |Q|
``soft_ge_04``  fraction of query words with credit >= 0.4
``soft_ge_06``  fraction of query words with credit >= 0.6
``best_mean``   mean credit over all query words
``len_ratio``   tanh(log((1+|P|)/(1+|Q|))) — passage vs question length

Training (``build_training_pairs``): train-split questions only. Each
question gives its own answer as a positive and negatives: the answer of
another question (same site) with the highest lexical coverage among
``HARD_POOL`` random ones (a *hard* negative that shares words) and
``n_random`` random answers. With ``mining="max_lex"`` (the PR #19 recipe)
the hard negative is picked from the whole pool; because coverage grows with
length, those negatives are much longer than real answers (median 66 vs 41
distinct words on the train split) and the classifier learns "long passage =
wrong answer". ``mining="length_matched"`` only considers pool answers whose
distinct-word count is within a factor ``LEN_BAND`` of the own answer
(falling back to the whole pool when none is). ``LogisticRegression`` (L2, C=1, balanced classes) on
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
FEATURES: tuple[str, ...] = (
    "lex",
    "soft",
    "weakest",
    "missing",
    "centroid",
    "jaccard",
    "hit_frac",
    "soft_ge_04",
    "soft_ge_06",
    "best_mean",
    "len_ratio",
)
LEXICAL_FEATURES: tuple[str, ...] = ("lex", "missing", "jaccard", "hit_frac", "len_ratio")
SIM_FLOOR = 0.0
HARD_POOL = 30
RANK_POOL = 50
SAMPLE_SEED = 17
LEN_BAND = 1.5
MINING = ("max_lex", "length_matched")
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
    credits = [credit[w] for w in q]
    union = len(set(q) | pset) or 1
    return {
        "lex": sum(ws[w] for w in hit) / total,
        "soft": sum(ws[w] * credit[w] for w in q) / total,
        "weakest": min((credit[w] for w in missing), default=1.0),
        "missing": len(missing) / len(q),
        "centroid": float(qv @ pv) if qv is not None and pv is not None else 0.0,
        "jaccard": len(hit) / union,
        "hit_frac": len(hit) / len(q),
        "soft_ge_04": sum(c >= 0.4 for c in credits) / len(q),
        "soft_ge_06": sum(c >= 0.6 for c in credits) / len(q),
        "best_mean": float(sum(credits) / len(q)),
        "len_ratio": float(math.tanh(math.log((1.0 + len(pset)) / (1.0 + len(q))))),
        "best": best,  # type: ignore[dict-item]
    }


def _row(f: Mapping[str, float], names: Sequence[str]) -> list[float]:
    return [float(f[n]) for n in names]


# ---------------------------------------------------------------------------
# training and out-of-sample evaluation (build time; needs the raw pages)


def build_training_pairs(
    pairs: Sequence[dict],
    idf: Mapping[str, float],
    seed: int = SAMPLE_SEED,
    *,
    mining: str = "max_lex",
    n_random: int = 1,
    band: float = LEN_BAND,
) -> list[tuple[list[str], list[str], int, str]]:
    """(q, passage, label, kind): one positive, one hard and ``n_random`` random negatives.

    The defaults reproduce the PR #19 sampling exactly (same RNG stream), so
    the out-of-sample triples in ``evaluate`` stay comparable across PRs.
    """
    if mining not in MINING:
        raise ValueError(f"mining must be one of {MINING}")
    if n_random < 1 or band < 1.0:
        raise ValueError("n_random >= 1 and band >= 1 required")
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
        if mining == "length_matched":
            n = len(set(p["a"]))
            pool = [o for o in pool if n / band <= len(set(o["a"])) <= n * band] or pool
        hard = max(pool, key=lambda o: (lex(p["q"], o["a"]), -o["aid"]))
        out.append((p["q"], hard["a"], 0, "hard"))
        others = [o for o in site if o is not p]
        for _ in range(n_random):
            out.append((p["q"], rng.choice(others)["a"], 0, "random"))
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


def length_profile(rows: Sequence[tuple[list[str], list[str], int, str]]) -> dict[str, dict[str, float]]:
    """Median / mean distinct passage words per row kind (own, hard, random)."""
    out: dict[str, dict[str, float]] = {}
    for kind in ("own", "hard", "random"):
        n = [len(set(a)) for _, a, _, k in rows if k == kind]
        if n:
            out[kind] = {"n": len(n), "median": float(np.median(n)), "mean": float(np.mean(n))}
    return out


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
    """AUC (own vs hard / random) and rank of the own answer among ``RANK_POOL``.

    ``vs_hard`` uses the PR #19 max-coverage hard negatives (comparable across
    PRs, but longer than real answers, so a length cue scores well on it);
    ``vs_hard_len`` uses length-matched hard negatives, where length carries
    no signal.
    """
    weight = lambda w: idf.get(w, 1.0)  # noqa: E731
    triples = build_training_pairs(test_pairs, idf, seed)
    feats = [pair_features(q, a, weight, dv) for q, a, _, _ in triples]
    kinds = [k for _, _, _, k in triples]
    lm = [t for t in build_training_pairs(test_pairs, idf, seed, mining="length_matched") if t[3] != "random"]
    lm_feats = [pair_features(q, a, weight, dv) for q, a, _, _ in lm]
    lm_kinds = [k for _, _, _, k in lm]

    def score(name: str, f) -> float:
        m = models[name]
        return f["lex"] if m is None else m.prob(f)

    auc: dict[str, dict[str, float]] = {}
    for name in models:
        s = [score(name, f) for f in feats]
        pos = [x for x, k in zip(s, kinds) if k == "own"]
        s_lm = [score(name, f) for f in lm_feats]
        auc[name] = {
            "vs_hard": _auc(pos, [x for x, k in zip(s, kinds) if k == "hard"]),
            "vs_hard_len": _auc(
                [x for x, k in zip(s_lm, lm_kinds) if k == "own"], [x for x, k in zip(s_lm, lm_kinds) if k == "hard"]
            ),
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
        "passage_length": {"max_lex": length_profile(triples), "length_matched": length_profile(lm)},
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


# ---------------------------------------------------------------------------
# null-control test (run time, opt-in): does the passage support *this* word?

NULL_SEED = 42
NULL_MIN_LEN = 4


def control_words(
    dv: DomainVectors, exclude: Iterable[str], k: int = 100, seed: int = NULL_SEED
) -> tuple[str, ...]:
    """``k`` seeded control words: alphabetic vector words of >= 4 letters outside ``exclude``.

    The pool is the sorted domain-vector vocabulary minus the corpus words, so
    no eval row and no corpus word chose the controls.
    """
    if k < 1:
        raise ValueError("k >= 1 required")
    ex = set(exclude)
    pool = sorted(w for w in dv.index if w.isalpha() and len(w) >= NULL_MIN_LEN and w not in ex)
    return tuple(random.Random(seed).sample(pool, min(k, len(pool))))


def null_percentile(
    model: "PassageSupportModel",
    q_words: Sequence[str],
    word: str,
    p_words: Iterable[str],
    weight: Callable[[str], float],
    controls: Sequence[str],
) -> float:
    """Fraction of controls that score *below* the real query word on this passage.

    Each control replaces ``word`` in the query and the classifier re-scores
    the same passage. A passage that answers the question should prefer the
    real word to unrelated ones; when an arbitrary word scores as high, the
    probability came from the rest of the query (the topic), not from this
    word, so the passage does not vouch for it.
    """
    p_list = list(p_words)
    real = model.verdict(q_words, p_list, weight)
    if real is None or not controls:
        return 0.0
    below = 0
    for c in controls:
        v = model.verdict([c if w == word else w for w in q_words], p_list, weight)
        below += int(v is not None and v.prob < real.prob)
    return below / len(controls)


@lru_cache(maxsize=2)
def _load_model(path: str) -> dict:
    return json.loads(Path(path).read_text())
