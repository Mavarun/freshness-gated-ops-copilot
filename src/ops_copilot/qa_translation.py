"""Question-answer translation model: does this *evidence* answer the question?

PR #14-#16 tried three word lists (general-English word vectors, Stack
Exchange tag synonyms, Wiktionary computing senses) and none moved a held-out
row: the senses the held-out rows need (``lag`` ~ latency, ``health`` ~
status, ``bounce`` ~ restart) are either absent or not phrased with the
corpus word. A word list substitutes a query word *before* looking at the
evidence. This module instead scores a (query word, evidence) pair: how likely
is it that a question containing ``lag`` is answered by text containing
``latency``?

Model. IBM Model 1 (Brown et al. 1993) trained in the question <- answer
direction, as in answer retrieval for Q&A archives (Berger et al. 2000; Xue,
Jeon & Croft 2008). The training data is *outside* data written by
practitioners who never saw this repo: the titles of the most-voted questions
of eight ops Stack Exchange sites and the accepted / top-voted answers to them
(``scripts/fetch_stackexchange_qa.py``; CC BY-SA, attribution in the table's
``meta``). ``T(q | a)`` is the probability that answer word ``a`` "generates"
question word ``q``; an empty (NULL) answer word absorbs title words that no
answer word explains. The support score of query word ``q`` given an evidence
word ``a`` is the lift

    score(q, a) = log( T(q | a) / P_title(q) )

i.e. how much more likely ``q`` is in the question when ``a`` is in its
answer than in a random title. It is evidence-conditioned, so it applies to a
*known* corpus word used in another sense (``lag`` is a corpus word via
"consumer lag"; a latency page lacks it, yet ``latency`` answers ``lag``
questions) as well as to unknown words.

Leakage. Nothing is filtered by eval words. Pairs are split train / test by a
salted hash of (site, question id) before training; the committed table is the
*train* model, and ``rank_eval`` reports answer-ranking quality on the test
questions (out of sample). The committed table keeps, for every *corpus*
content word ``a`` (the evidence side), its top question words; the corpus
vocabulary hash is pinned so a corpus change without a rebuild fails a test.
The question side is the whole title vocabulary (min document frequency
``MIN_Q_DF``), not the eval's words.

Tokens: ``text.content_tokens`` of the normalised text, plain alphabetic words
only (identifiers and numbers are exact-only everywhere in this repo), plural
folded with ``text.fold_token``. Answers drop fenced / indented code, inline
code, URLs and HTML, and keep the first ``MAX_ANSWER_TOKENS`` distinct words.
"""

from __future__ import annotations

import gzip
import hashlib
import json
import math
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Sequence

import numpy as np

from ops_copilot.text import content_tokens, fold_token, is_identifier

DATA_DIR = Path(__file__).resolve().parents[2] / "data" / "qa"
DEFAULT_TABLE = DATA_DIR / "se_qa_translation.json.gz"
SPLIT_SALT = "se-qa-translation-split"
VALID_SALT = "se-qa-translation-valid"
TEST_FRACTION = 0.10
VALID_FRACTION = 0.10  # of the train questions; picks the EM iteration count
ITERATION_GRID: tuple[int, ...] = (1, 2, 3, 5, 8)
MAX_TITLE_TOKENS = 12
MAX_ANSWER_TOKENS = 80
MAX_ANSWERS_PER_QUESTION = 2
MIN_Q_DF = 3
MIN_A_DF = 5
EM_ITERATIONS = 8  # upper end of ITERATION_GRID; the build picks on validation
SHRINK_ALPHA = 5.0
TABLE_TOP_Q = 300
TABLE_MIN_LIFT = 1.0  # keep pairs at least e x background; the gate threshold is calibrated above it
NULL = "<null>"

_FENCE = re.compile(r"```.*?```|~~~.*?~~~", re.S)
_INDENTED = re.compile(r"(?m)^(?: {4}|\t).*$")
_INLINE_CODE = re.compile(r"`[^`\n]*`")
_URL = re.compile(r"https?://\S+|www\.\S+")
_HTML = re.compile(r"<[^>]+>")
_ENTITY = re.compile(r"&[a-z]+;|&#\d+;")
_MD_LINK = re.compile(r"\[([^\]]*)\]\([^)]*\)")


def clean_markdown(text: str) -> str:
    """Prose of a Stack Exchange markdown body (code, links and HTML removed)."""
    t = _FENCE.sub(" ", text or "")
    t = _INDENTED.sub(" ", t)
    t = _INLINE_CODE.sub(" ", t)
    t = _MD_LINK.sub(r"\1", t)
    t = _URL.sub(" ", t)
    t = _HTML.sub(" ", t)
    t = _ENTITY.sub(" ", t)
    return t


def words(text: str) -> list[str]:
    """Plain alphabetic content words, plural-folded, in order (with repeats)."""
    out: list[str] = []
    for tok in content_tokens(text):
        if not tok.isalpha() or is_identifier(tok):
            continue
        out.append(fold_token(tok))
    return out


def distinct(seq: Iterable[str], limit: int) -> list[str]:
    seen: dict[str, None] = {}
    for w in seq:
        if w not in seen:
            seen[w] = None
            if len(seen) >= limit:
                break
    return list(seen)


def _hash_unit(salt: str, site: str, question_id: int) -> float:
    h = hashlib.sha1(f"{salt}|{site}|{int(question_id)}".encode()).hexdigest()
    return int(h[:8], 16) / 0xFFFFFFFF


def is_test(site: str, question_id: int, fraction: float = TEST_FRACTION) -> bool:
    """Deterministic train / test assignment of one question (salted SHA-1)."""
    return _hash_unit(SPLIT_SALT, site, question_id) < fraction


def is_valid(site: str, question_id: int, fraction: float = VALID_FRACTION) -> bool:
    """Validation questions inside train (independent salt); never test ones."""
    return not is_test(site, question_id) and _hash_unit(VALID_SALT, site, question_id) < fraction


def pairs_from_page(site: str, body: dict) -> list[dict]:
    """(title words, answer words) pairs of one raw API page.

    Up to ``MAX_ANSWERS_PER_QUESTION`` answers per question with score >= 1,
    the accepted one first, then by score. Licences are kept for attribution.
    """
    out: list[dict] = []
    for q in body.get("items", []):
        title = words(q.get("title", ""))
        title = distinct(title, MAX_TITLE_TOKENS)
        if not title:
            continue
        answers = [a for a in q.get("answers") or [] if int(a.get("score", 0)) >= 1]
        answers.sort(key=lambda a: (not a.get("is_accepted", False), -int(a.get("score", 0)), int(a["answer_id"])))
        for a in answers[:MAX_ANSWERS_PER_QUESTION]:
            aw = distinct(words(clean_markdown(a.get("body_markdown", ""))), MAX_ANSWER_TOKENS)
            if not aw:
                continue
            out.append(
                {
                    "site": site,
                    "qid": int(q["question_id"]),
                    "aid": int(a["answer_id"]),
                    "license": a.get("content_license", "CC BY-SA"),
                    "q": title,
                    "a": aw,
                }
            )
    return out


@dataclass
class Model1:
    """Trained IBM Model 1: ``prob[k]`` = T(q_vocab[qk[k]] | a_vocab[ak[k]])."""

    q_vocab: list[str]
    a_vocab: list[str]  # index 0 is NULL
    qk: np.ndarray
    ak: np.ndarray
    prob: np.ndarray
    count: np.ndarray  # expected alignment counts of the last E-step
    q_bg: np.ndarray  # P_title(q), title-token unigram probability
    log: list[dict]

    def matrix(self):
        from scipy.sparse import csr_matrix

        return csr_matrix(
            (self.prob, (self.ak, self.qk)), shape=(len(self.a_vocab), len(self.q_vocab))
        )


def train_model1(
    pairs: Sequence[dict],
    *,
    iterations: int = EM_ITERATIONS,
    min_q_df: int = MIN_Q_DF,
    min_a_df: int = MIN_A_DF,
) -> Model1:
    """EM for IBM Model 1, fully vectorised (deterministic; no randomness).

    Every title word of a pair aligns to one of that pair's answer words or
    NULL. Initialisation is uniform over co-occurring pairs, so the result is
    fixed by the data alone.
    """
    from collections import Counter

    qdf: Counter[str] = Counter()
    adf: Counter[str] = Counter()
    for p in pairs:
        qdf.update(set(p["q"]))
        adf.update(set(p["a"]))
    q_vocab = sorted(w for w, c in qdf.items() if c >= min_q_df)
    a_vocab = [NULL, *sorted(w for w, c in adf.items() if c >= min_a_df)]
    qi = {w: i for i, w in enumerate(q_vocab)}
    ai = {w: i for i, w in enumerate(a_vocab)}
    seg_q: list[np.ndarray] = []
    seg_a: list[np.ndarray] = []
    seg_id: list[np.ndarray] = []
    q_tokens = np.zeros(len(q_vocab), dtype=np.float64)
    sid = 0
    for p in pairs:
        qs = [qi[w] for w in p["q"] if w in qi]
        if not qs:
            continue
        as_ = np.array([0, *(ai[w] for w in p["a"] if w in ai)], dtype=np.int32)
        for q in qs:
            q_tokens[q] += 1.0
            seg_q.append(np.full(len(as_), q, dtype=np.int32))
            seg_a.append(as_)
            seg_id.append(np.full(len(as_), sid, dtype=np.int32))
            sid += 1
    occ_q = np.concatenate(seg_q)
    occ_a = np.concatenate(seg_a)
    occ_s = np.concatenate(seg_id)
    del seg_q, seg_a, seg_id
    key = occ_a.astype(np.int64) * len(q_vocab) + occ_q
    uniq, inv = np.unique(key, return_inverse=True)
    inv = inv.astype(np.int64)
    ak = (uniq // len(q_vocab)).astype(np.int32)
    qk = (uniq % len(q_vocab)).astype(np.int32)
    del key, occ_q, occ_a
    prob = np.full(len(uniq), 1.0 / len(q_vocab), dtype=np.float64)
    log: list[dict] = []
    count = np.zeros(len(uniq))
    for it in range(iterations):
        t = prob[inv]
        denom = np.bincount(occ_s, weights=t, minlength=sid)
        post = t / denom[occ_s]
        count = np.bincount(inv, weights=post, minlength=len(uniq))
        a_tot = np.bincount(ak, weights=count, minlength=len(a_vocab))
        prob = count / a_tot[ak]
        log.append({"iteration": it + 1, "log_likelihood": float(np.log(denom).sum())})
    q_bg = q_tokens / q_tokens.sum()
    return Model1(q_vocab, a_vocab, qk, ak, prob, count, q_bg, log)


def lift_scores(model: Model1, alpha: float = None) -> np.ndarray:  # type: ignore[assignment]
    """Shrunk lift ``log T~(q|a) / P_title(q)`` for every stored (a, q) entry.

    ``T~(q|a) = (c(q,a) + alpha * P_title(q)) / (c(a) + alpha)`` with the
    expected alignment counts ``c`` of the last E-step: a pair seen in a
    fraction of one question cannot reach a high lift by luck. ``alpha``
    (``SHRINK_ALPHA``) is fixed before any eval, not tuned.
    """
    a = SHRINK_ALPHA if alpha is None else float(alpha)
    a_tot = np.bincount(model.ak, weights=model.count, minlength=len(model.a_vocab))
    bg = model.q_bg[model.qk]
    shrunk = (model.count + a * bg) / (a_tot[model.ak] + a)
    return np.log(shrunk) - np.log(bg)


def query_log_likelihood(
    model: Model1, q_words: Sequence[str], a_words: Sequence[str], *, lam: float = 0.2
) -> float:
    """Model-1 log P(question | answer), smoothed with the title unigram.

    Used to rank candidate answers in ``rank_eval``. ``lam`` is fixed, not tuned.
    """
    qi = {w: i for i, w in enumerate(model.q_vocab)}
    ai = {w: i for i, w in enumerate(model.a_vocab)}
    mat = model._csr if hasattr(model, "_csr") else model.matrix()
    model._csr = mat  # type: ignore[attr-defined]
    rows = [0, *(ai[w] for w in set(a_words) if w in ai)]
    sub = mat[rows]
    total = 0.0
    floor = 1.0 / (len(model.q_vocab) * 10.0)
    for w in q_words:
        j = qi.get(w)
        if j is None:
            continue
        p_t = float(sub[:, j].sum()) / len(rows)
        p = (1.0 - lam) * p_t + lam * float(model.q_bg[j])
        total += math.log(max(p, floor))
    return total


def _bm25_rank_scores(q_words: Sequence[str], cands: Sequence[Sequence[str]], idf: dict[str, float]) -> list[float]:
    out = []
    avg = sum(len(c) for c in cands) / max(len(cands), 1)
    for c in cands:
        cs = set(c)
        s = 0.0
        for w in set(q_words):
            if w in cs:
                s += idf.get(w, 0.0) * (2.2 / (1.0 + 1.2 * (0.25 + 0.75 * len(c) / max(avg, 1))))
        out.append(s)
    return out


def rank_eval(
    model: Model1,
    test_pairs: Sequence[dict],
    train_pairs: Sequence[dict],
    *,
    n_candidates: int = 50,
    seed: int = 42,
    max_queries: int = 1000,
) -> dict:
    """Out-of-sample answer ranking: true answer vs ``n_candidates - 1`` others.

    For each test question (first answer only), the candidates are its own
    answer plus answers of other *test* questions drawn with a fixed seed. Three
    scorers rank them: BM25 on exact words, the translation model, and their
    rank-average. Reported: precision@1 and MRR, plus the share of test
    questions whose true answer shares *no* word with the title (where an
    exact-match gate has nothing to go on).
    """
    rng = np.random.default_rng(seed)
    firsts: dict[tuple[str, int], dict] = {}
    for p in test_pairs:
        firsts.setdefault((p["site"], p["qid"]), p)
    qs = list(firsts.values())
    if len(qs) > max_queries:
        idx = rng.choice(len(qs), size=max_queries, replace=False)
        qs = [qs[i] for i in sorted(idx)]
    pool = [p["a"] for p in firsts.values()]
    n_docs = len(train_pairs)
    df: dict[str, int] = {}
    for p in train_pairs:
        for w in set(p["a"]):
            df[w] = df.get(w, 0) + 1
    idf = {w: math.log((n_docs - c + 0.5) / (c + 0.5) + 1.0) for w, c in df.items()}
    res = {"bm25": [], "translation": [], "combined": []}
    no_overlap = []
    for p in qs:
        others = [a for a in pool if a is not p["a"]]
        pick = rng.choice(len(others), size=min(n_candidates - 1, len(others)), replace=False)
        cands = [p["a"], *(others[i] for i in pick)]
        b = np.array(_bm25_rank_scores(p["q"], cands, idf))
        t = np.array([query_log_likelihood(model, p["q"], c) for c in cands])
        rb = _ranks(b)
        rt = _ranks(t)
        rc = _ranks(-(rb + rt))  # lower average rank = better
        for name, r in (("bm25", rb), ("translation", rt), ("combined", rc)):
            res[name].append(int(r[0]))
        no_overlap.append(not (set(p["q"]) & set(p["a"])))
    out: dict = {"n_queries": len(qs), "n_candidates": n_candidates, "seed": seed}
    no = np.array(no_overlap)
    out["share_no_title_overlap"] = float(no.mean()) if len(no) else 0.0
    for name, ranks in res.items():
        r = np.array(ranks)
        out[name] = {
            "p_at_1": float((r == 1).mean()),
            "mrr": float((1.0 / r).mean()),
            "p_at_1_no_overlap": float((r[no] == 1).mean()) if no.any() else None,
        }
    return out


def _ranks(scores: np.ndarray) -> np.ndarray:
    """1-based rank of each candidate, ties broken pessimistically for index 0."""
    s = np.asarray(scores, dtype=float)
    # rank of candidate i = 1 + number of candidates with score >= s[i] except itself
    return np.array([1 + int(((s >= s[i]).sum()) - 1) for i in range(len(s))])


# --- committed, corpus-bound table -------------------------------------------------


def corpus_words(corpus_texts: Sequence[str]) -> list[str]:
    return sorted({w for t in corpus_texts for w in words(t)})


def corpus_hash(corpus_texts: Sequence[str]) -> str:
    return hashlib.sha256("\n".join(corpus_words(corpus_texts)).encode()).hexdigest()


def build_table(model: Model1, corpus_texts: Sequence[str], meta: dict) -> dict:
    """For each corpus word ``a``: its top question words by T(q|a), with lift."""
    lift = lift_scores(model)
    vocab = corpus_words(corpus_texts)
    a_index = {w: i for i, w in enumerate(model.a_vocab)}
    order = np.lexsort((model.qk, -lift, model.ak))
    starts = np.searchsorted(model.ak[order], np.arange(len(model.a_vocab) + 1))
    table: dict[str, list[list]] = {}
    for w in vocab:
        i = a_index.get(w)
        if i is None:
            continue
        idx = order[starts[i] : starts[i + 1]]
        rows = [
            [model.q_vocab[model.qk[k]], round(float(lift[k]), 4), round(float(model.prob[k]), 6), round(float(model.count[k]), 3)]
            for k in idx
            if lift[k] >= TABLE_MIN_LIFT
        ][:TABLE_TOP_Q]
        if rows:
            table[w] = rows
    meta = dict(meta)
    meta["corpus_words"] = len(vocab)
    meta["corpus_words_in_model"] = sum(1 for w in vocab if w in a_index)
    meta["corpus_hash"] = corpus_hash(corpus_texts)
    meta["columns"] = ["question_word", "lift_log", "t_prob", "expected_count"]
    meta["shrink_alpha"] = SHRINK_ALPHA
    meta["table_min_lift"] = TABLE_MIN_LIFT
    meta["table_top_q"] = TABLE_TOP_Q
    return {"meta": meta, "table": table}


def _payload(table: dict) -> bytes:
    return json.dumps(table, sort_keys=True, separators=(",", ":")).encode()


def dump_table(table: dict, path: Path = DEFAULT_TABLE) -> str:
    raw = _payload(table)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(gzip.compress(raw, compresslevel=9, mtime=0))
    return hashlib.sha256(raw).hexdigest()


def load_table(path: Path = DEFAULT_TABLE) -> dict:
    return json.loads(gzip.decompress(Path(path).read_bytes()))


@dataclass(frozen=True)
class Translation:
    """Best evidence word supporting one query word, and its lift."""

    query_word: str
    evidence_word: str
    score: float


class AnswerSupportModel:
    """Score whether evidence words answer a query word (committed table only)."""

    def __init__(
        self,
        corpus_texts: Sequence[str] | None = None,
        *,
        min_score: float = 3.0,
        path: Path = DEFAULT_TABLE,
        check_corpus: bool = True,
    ) -> None:
        data = load_table(path)
        self.meta = data["meta"]
        if check_corpus and corpus_texts is not None:
            h = corpus_hash(corpus_texts)
            if h != self.meta["corpus_hash"]:
                raise ValueError(
                    "corpus changed since the QA translation table was built; "
                    "rerun scripts/build_qa_translation.py"
                )
        self.min_score = float(min_score)
        # inverted: question word -> {evidence word: lift}
        inv: dict[str, dict[str, float]] = {}
        for a, rows in data["table"].items():
            for q, lift, _p, _c in rows:
                inv.setdefault(q, {})[a] = float(lift)
        self._inv = inv

    def candidates(self, query_word: str) -> dict[str, float]:
        """Evidence words that answer ``query_word`` and their lifts (any score)."""
        return dict(self._inv.get(fold_token(query_word), {}))

    def best(self, query_word: str, evidence_words: Iterable[str]) -> Translation | None:
        """Highest-lift evidence word for ``query_word`` (itself excluded), any score."""
        q = fold_token(query_word)
        cands = self._inv.get(q)
        if not cands:
            return None
        best: Translation | None = None
        for e in evidence_words:
            ef = fold_token(e)
            if ef == q:
                continue
            s = cands.get(ef)
            if s is not None and (best is None or s > best.score or (s == best.score and ef < best.evidence_word)):
                best = Translation(q, ef, s)
        return best

    def supports(self, query_word: str, evidence_words: Iterable[str]) -> Translation | None:
        t = self.best(query_word, evidence_words)
        return t if t is not None and t.score >= self.min_score else None
