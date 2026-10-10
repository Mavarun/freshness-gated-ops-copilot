"""Ops-domain word vectors: PPMI + truncated SVD over Stack Exchange prose.

Every outside resource tried so far links words by *dictionary* sense
(counter-fitted vectors, Wiktionary, tag synonyms) or by question <- answer
alignment (``qa_translation``). None of them sees how practitioners *use* a
word next to other words. A distributional model does: two words that occur
in the same contexts ("the replication ___ is high", "___ the service after
the config change") get similar vectors, whether or not a dictionary lists
them as synonyms. It is also the known weak point of such models: antonyms
and co-hyponyms (``start`` / ``stop``, ``read`` / ``write``) share contexts
too, which is why this module only produces a similarity and never a
substitution. The decision is left to ``passage_support``.

Training data: the same committed-by-hash Stack Exchange snapshot as
``qa_translation`` (raw pages pinned by ``meta.raw_sha256``; the build
script refuses a different snapshot). Prose of question titles and of up to
``MAX_ANSWERS_PER_QUESTION`` answers per question, code / links / HTML
removed, ``qa_translation.words`` tokens (plain alphabetic, plural-folded).
**Only train-split questions** (``qa_translation.is_test`` is false) are used,
so the test-split evaluation in ``passage_support`` is out of sample.
Nothing is filtered by eval or corpus words.

Method (Levy, Goldberg & Dagan 2015, fixed a priori, nothing tuned here):
symmetric window of ``WINDOW`` words weighted 1/distance, vocabulary = the
``VOCAB_SIZE`` most frequent words with count >= ``MIN_COUNT``, positive PMI
with context-distribution smoothing ``CDS_ALPHA`` = 0.75, truncated SVD
(``sklearn`` randomized, ``random_state=0``) to ``DIM`` dimensions with
eigenvalue weighting ``EIG_P`` = 0.5, rows L2-normalised. ``DIM`` is small
because the committed file must stay under the repo's 512 KB data cap.

Committed form (``data/domainvec/se_ppmi_svd.json.gz``): words plus int8
vectors (unit vectors x 127, base64), zero-mtime gzip so a rebuild from the
same snapshot is byte-identical. It contains word statistics only, no post
text, under CC BY-SA 4.0 with attribution (``data/domainvec/NOTICE.md``).
"""

from __future__ import annotations

import base64
import gzip
import hashlib
import io
import json
from collections import Counter
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Iterable, Sequence

import numpy as np

from ops_copilot.qa_translation import (
    MAX_ANSWERS_PER_QUESTION,
    clean_markdown,
    is_test,
    words,
)

DATA_DIR = Path(__file__).resolve().parents[2] / "data" / "domainvec"
DEFAULT_TABLE = DATA_DIR / "se_ppmi_svd.json.gz"
WINDOW = 4
MIN_COUNT = 20
VOCAB_SIZE = 6000
CDS_ALPHA = 0.75
DIM = 48
EIG_P = 0.5
SVD_SEED = 0
MAX_DOC_TOKENS = 400


def docs_from_page(site: str, body: dict) -> list[dict]:
    """One token sequence per question: title, then its top answers' prose."""
    out: list[dict] = []
    for q in body.get("items", []):
        answers = [a for a in q.get("answers") or [] if int(a.get("score", 0)) >= 1]
        if not answers:
            continue
        answers.sort(key=lambda a: (not a.get("is_accepted", False), -int(a.get("score", 0)), int(a["answer_id"])))
        seqs = [words(q.get("title", ""))]
        for a in answers[:MAX_ANSWERS_PER_QUESTION]:
            seqs.append(words(clean_markdown(a.get("body_markdown", "")))[:MAX_DOC_TOKENS])
        out.append({"site": site, "qid": int(q["question_id"]), "seqs": [s for s in seqs if s]})
    return out


def train_docs(docs: Iterable[dict]) -> list[list[str]]:
    """Token sequences of train-split questions only (each title / answer separately)."""
    seen: set[tuple[str, int]] = set()
    out: list[list[str]] = []
    for d in docs:
        key = (d["site"], d["qid"])
        if key in seen or is_test(d["site"], d["qid"]):
            continue
        seen.add(key)
        out.extend(d["seqs"])
    return out


@dataclass
class DomainVectors:
    words: list[str]
    vectors: np.ndarray  # (n, DIM) float32, unit rows
    meta: dict

    def __post_init__(self) -> None:
        self.index = {w: i for i, w in enumerate(self.words)}

    def __contains__(self, word: str) -> bool:
        return word in self.index

    def vector(self, word: str) -> np.ndarray | None:
        i = self.index.get(word)
        return None if i is None else self.vectors[i]

    def similarity(self, a: str, b: str) -> float | None:
        ia, ib = self.index.get(a), self.index.get(b)
        if ia is None or ib is None:
            return None
        return float(self.vectors[ia] @ self.vectors[ib])

    def best(self, word: str, candidates: Iterable[str]) -> tuple[str | None, float]:
        """Most similar candidate word and its cosine (``(None, 0.0)`` if none known)."""
        v = self.vector(word)
        cands = [c for c in dict.fromkeys(candidates) if c in self.index and c != word]
        if v is None or not cands:
            return None, 0.0
        sims = self.vectors[[self.index[c] for c in cands]] @ v
        k = int(np.argmax(sims))
        return cands[k], float(sims[k])

    def neighbours(self, word: str, k: int = 10) -> list[tuple[str, float]]:
        v = self.vector(word)
        if v is None:
            return []
        sims = self.vectors @ v
        order = np.argsort(-sims, kind="stable")
        return [(self.words[i], float(sims[i])) for i in order[: k + 1] if self.words[i] != word][:k]


def train_vectors(seqs: Sequence[Sequence[str]], meta: dict | None = None) -> DomainVectors:
    from scipy.sparse import coo_matrix, csr_matrix
    from sklearn.decomposition import TruncatedSVD

    counts = Counter(w for s in seqs for w in s)
    vocab = [w for w, c in sorted(counts.items(), key=lambda x: (-x[1], x[0])) if c >= MIN_COUNT][:VOCAB_SIZE]
    index = {w: i for i, w in enumerate(vocab)}
    n = len(vocab)
    rows, cols, vals = [], [], []
    for s in seqs:
        ids = np.array([index.get(w, -1) for w in s], dtype=np.int64)
        for d in range(1, WINDOW + 1):
            if len(ids) <= d:
                break
            a, b = ids[:-d], ids[d:]
            keep = (a >= 0) & (b >= 0)
            if keep.any():
                rows.append(a[keep])
                cols.append(b[keep])
                vals.append(np.full(int(keep.sum()), 1.0 / d))
    r = np.concatenate(rows)
    c = np.concatenate(cols)
    v = np.concatenate(vals)
    m = coo_matrix((np.concatenate([v, v]), (np.concatenate([r, c]), np.concatenate([c, r]))), shape=(n, n)).tocsr()
    m.sum_duplicates()
    total = m.sum()
    row_sum = np.asarray(m.sum(axis=1)).ravel()
    ctx = np.asarray(m.sum(axis=0)).ravel() ** CDS_ALPHA
    ctx = ctx / ctx.sum()
    coo = m.tocoo()
    pmi = np.log((coo.data / total) / ((row_sum[coo.row] / total) * ctx[coo.col]))
    keep = pmi > 0
    ppmi = csr_matrix((pmi[keep], (coo.row[keep], coo.col[keep])), shape=(n, n))
    svd = TruncatedSVD(n_components=DIM, algorithm="randomized", n_iter=7, random_state=SVD_SEED)
    u = svd.fit_transform(ppmi)  # = U * S
    s = svd.singular_values_
    vec = u / s * (s**EIG_P)
    # deterministic sign: largest-magnitude coordinate of each component positive
    signs = np.sign(vec[np.argmax(np.abs(vec), axis=0), np.arange(DIM)])
    vec = vec * signs
    vec = vec / np.maximum(np.linalg.norm(vec, axis=1, keepdims=True), 1e-12)
    info = {
        "n_sequences": len(seqs),
        "n_tokens": int(sum(len(s) for s in seqs)),
        "vocab": n,
        "window": WINDOW,
        "min_count": MIN_COUNT,
        "vocab_size_cap": VOCAB_SIZE,
        "cds_alpha": CDS_ALPHA,
        "dim": DIM,
        "eig_p": EIG_P,
        "svd_seed": SVD_SEED,
        "nnz_ppmi": int(ppmi.nnz),
    }
    return DomainVectors(vocab, vec.astype(np.float32), {**(meta or {}), **info})


def _quantize(vec: np.ndarray) -> np.ndarray:
    return np.clip(np.round(vec * 127.0), -127, 127).astype(np.int8)


def dump_table(dv: DomainVectors, path: Path = DEFAULT_TABLE) -> str:
    """Byte-stable gzip JSON (zero mtime); returns the payload SHA-256."""
    q = _quantize(dv.vectors)
    payload = json.dumps(
        {
            "meta": dv.meta,
            "words": dv.words,
            "dim": int(q.shape[1]),
            "int8_b64": base64.b64encode(q.tobytes()).decode("ascii"),
        },
        sort_keys=True,
        separators=(",", ":"),
    ).encode()
    buf = io.BytesIO()
    with gzip.GzipFile(fileobj=buf, mode="wb", mtime=0, compresslevel=9) as gz:
        gz.write(payload)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(buf.getvalue())
    return hashlib.sha256(payload).hexdigest()


def load_table(path: str | Path | None = None) -> DomainVectors:
    raw = json.loads(gzip.decompress(Path(path or DEFAULT_TABLE).read_bytes()))
    q = np.frombuffer(base64.b64decode(raw["int8_b64"]), dtype=np.int8).reshape(-1, raw["dim"])
    vec = q.astype(np.float32)
    vec /= np.maximum(np.linalg.norm(vec, axis=1, keepdims=True), 1e-12)
    return DomainVectors(list(raw["words"]), vec, raw["meta"])


@lru_cache(maxsize=2)
def default_vectors(path: str | None = None) -> DomainVectors:
    return load_table(path)
