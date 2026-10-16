"""Ops noun gloss-sense model: definitional bridges for the read path.

The verb gloss-sense backoff (``gloss_sense.py``) fixed held-out *write*
paraphrases (bounce/reboot -> restart) but left held-out *answer* rows at
0 of 9. Hard pairs such as ``lag~latency`` (domain-vector cosine 0.33 —
LACP sense) and ``health~status`` need an ops-specific *noun* sense model;
verb glosses do not cover them, and Wiktionary's computing-topic extract
has no useful ``latency`` / ``health`` / ``status`` headwords.

This module builds an undirected definitional graph over *all* Wiktionary
computing senses (any POS) plus a small committed ops-noun seed
(``data/wiktionary/ops_noun_senses.json``) for senses the topic filter
omits:

- listed synonym <-> headword (weight 2);
- pointer gloss ("Synonym of X") <-> X (weight 2);
- every alphabetic gloss content token <-> headword (weight 1), including
  tokens that are *not* themselves Wiktionary headwords.

The last rule is the key extension of the verb graph: ``laggy``'s gloss
("tending to lag ... because of network latency") links both ``lag`` and
``latency`` as nodes, so ``lag`` reaches ``latency`` in two hops. The ops
seed supplies definitional glosses for ``health`` / ``status`` / ``state``
/ ``latency`` / ``lag`` so shared genus words (condition, operational,
delay, response) create the same kind of bridge — not a synonym table.

Paths are gated by the *max* domain-vector cosine over sense-pair gloss
centroids (so a crowded headword like ``state`` is not diluted by
finite-state-machine senses). Default ``min_gloss_cosine`` 0.85 rejects
false bridges such as ``scan~image`` that broke a clean no-evidence trap
when the verb graph was wired into grounding.

``neighbours`` returns corpus words reachable under the gate, for
grounding alts and the retrieval rewrite. Calibrated on clean golden +
*dev* synonym rows only; held-out words may appear in the external
extract / seed (editors never saw this eval) but never in product
lexicons. Ships off until a held-out run meets the go / no-go rule.
"""

from __future__ import annotations

import json
from collections import defaultdict, deque
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import numpy as np

from ops_copilot.domain_vectors import DomainVectors, default_vectors
from ops_copilot.gloss_sense import (
    DEFAULT_MAX_HOPS,
    MIN_WORD_LEN,
    WEIGHT_GLOSS,
    WEIGHT_SYNONYM,
    BridgeHit,
    gloss_tokens,
)
from ops_copilot.semantic import Neighbour
from ops_copilot.text import fold_token, is_identifier, normalize_text
from ops_copilot.wiktionary_senses import load_extract

DATA_DIR = Path(__file__).resolve().parents[2] / "data" / "wiktionary"
DEFAULT_OPS_NOUN_SEED = DATA_DIR / "ops_noun_senses.json"
DEFAULT_MIN_GLOSS_COSINE = 0.85
DEFAULT_MAX_NEIGHBOURS = 2
DEFAULT_MIN_SCORE = 0.9


def load_ops_noun_senses(path: Path | None = None) -> list[dict]:
    """Committed ops noun seed (definitional glosses, Wiktionary schema)."""
    raw = json.loads((path or DEFAULT_OPS_NOUN_SEED).read_text(encoding="utf-8"))
    return list(raw.get("senses") or [])


@lru_cache(maxsize=1)
def all_senses() -> tuple[dict, ...]:
    """Wiktionary computing senses plus the ops noun seed."""
    return tuple(list(load_extract()["senses"]) + load_ops_noun_senses())


@lru_cache(maxsize=1)
def build_sense_graph() -> dict[str, list[tuple[str, int, str]]]:
    """Undirected all-POS sense graph; gloss tokens are nodes even if not heads."""
    adj: dict[str, dict[str, tuple[int, str]]] = defaultdict(dict)

    def link(a: str, b: str, weight: int, kind: str) -> None:
        if a == b or len(a) < MIN_WORD_LEN or len(b) < MIN_WORD_LEN:
            return
        for x, y in ((a, b), (b, a)):
            prev = adj[x].get(y)
            if prev is None or weight > prev[0]:
                adj[x][y] = (weight, kind)

    for s in all_senses():
        h = s["word"]
        gloss = s.get("gloss") or ""
        text = normalize_text(gloss)
        pointer = any(
            text.startswith(p)
            for p in (
                "synonym of ",
                "alternative form of ",
                "abbreviation of ",
                "short for ",
            )
        )
        for syn in s.get("synonyms") or []:
            if isinstance(syn, str) and syn.isalpha():
                link(h, syn.lower(), WEIGHT_SYNONYM, "synonym")
        toks = gloss_tokens(gloss)
        if pointer and toks:
            link(h, toks[0], WEIGHT_SYNONYM, "pointer")
        for tok in toks:
            link(h, tok, WEIGHT_GLOSS, "gloss")
    return {
        w: [(n, wt, kind) for n, (wt, kind) in sorted(nbrs.items())]
        for w, nbrs in sorted(adj.items())
    }


def _sense_centroid(sense: dict, vectors: DomainVectors) -> np.ndarray | None:
    toks = gloss_tokens(sense.get("gloss") or "")
    toks.extend(
        syn.lower()
        for syn in (sense.get("synonyms") or [])
        if isinstance(syn, str) and syn.isalpha()
    )
    word = sense["word"]
    vecs = [vectors.vector(t) for t in toks if t != word and vectors.vector(t) is not None]
    if not vecs:
        own = vectors.vector(word)
        return None if own is None else own.astype(np.float64)
    v = np.mean(np.stack(vecs), axis=0)
    n = float(np.linalg.norm(v))
    return v / n if n > 0 else None


@lru_cache(maxsize=1)
def _senses_by_word() -> dict[str, tuple[dict, ...]]:
    out: dict[str, list[dict]] = defaultdict(list)
    for s in all_senses():
        out[s["word"]].append(s)
    return {w: tuple(ss) for w, ss in out.items()}


def sense_gloss_cosine(
    a: str, b: str, vectors: DomainVectors | None = None
) -> float | None:
    """Max domain-vector cosine over sense-pair gloss centroids."""
    dv = vectors if vectors is not None else default_vectors()
    best: float | None = None
    for sa in _senses_by_word().get(a, ()):
        va = _sense_centroid(sa, dv)
        if va is None:
            continue
        for sb in _senses_by_word().get(b, ()):
            vb = _sense_centroid(sb, dv)
            if vb is None:
                continue
            c = float(va @ vb)
            if best is None or c > best:
                best = c
    return best


def noun_bridges_from(
    start: str,
    *,
    max_hops: int = DEFAULT_MAX_HOPS,
    vectors: DomainVectors | None = None,
) -> dict[str, BridgeHit]:
    """Shortest-path definitional bridges from ``start`` on the noun/all-POS graph."""
    graph = build_sense_graph()
    tok = start.lower()
    if tok not in graph and fold_token(tok) in graph:
        tok = fold_token(tok)
    if tok not in graph:
        return {}
    best: dict[str, tuple[int, float, str | None]] = {tok: (0, 0.0, None)}
    q: deque[str] = deque([tok])
    while q:
        u = q.popleft()
        hops, weight, _ = best[u]
        if hops >= max_hops:
            continue
        for v, wt, _kind in graph.get(u, ()):
            nh, nw = hops + 1, weight + float(wt)
            prev = best.get(v)
            if prev is None or nh < prev[0] or (nh == prev[0] and nw > prev[1]):
                best[v] = (nh, nw, u)
                q.append(v)

    def path_to(word: str) -> tuple[str, ...]:
        out: list[str] = []
        cur: str | None = word
        while cur is not None:
            out.append(cur)
            cur = best[cur][2]
        return tuple(reversed(out))

    dv = vectors if vectors is not None else default_vectors()
    hits: dict[str, BridgeHit] = {}
    for word, (hops, weight, _) in best.items():
        if word == tok or hops == 0:
            continue
        hits[word] = BridgeHit(
            word=word,
            hops=hops,
            weight=weight,
            path=path_to(word),
            gloss_cosine=sense_gloss_cosine(tok, word, dv),
        )
    return hits


@dataclass
class NounGlossSenseBackoff:
    """Definitional-sense backoff for noun/read-path grounding and retrieve."""

    max_hops: int = DEFAULT_MAX_HOPS
    min_score: float = DEFAULT_MIN_SCORE
    min_gloss_cosine: float = DEFAULT_MIN_GLOSS_COSINE
    max_neighbours: int = DEFAULT_MAX_NEIGHBOURS
    corpus_words: frozenset[str] | None = None

    def __post_init__(self) -> None:
        self._vectors = default_vectors()
        self._cache: dict[str, dict[str, BridgeHit]] = {}

    def _hits(self, token: str) -> dict[str, BridgeHit]:
        tok = token.lower()
        if tok not in self._cache:
            self._cache[tok] = noun_bridges_from(
                tok, max_hops=self.max_hops, vectors=self._vectors
            )
        return self._cache[tok]

    @staticmethod
    def lookupable(token: str) -> bool:
        return (
            token.isalpha()
            and not is_identifier(token)
            and len(token) >= MIN_WORD_LEN
        )

    def score_hit(self, hit: BridgeHit) -> float:
        cos = hit.gloss_cosine if hit.gloss_cosine is not None else 0.0
        # Prefer high sense-pair cosine; hops/weight break ties.
        return cos + 0.15 * (3 - hit.hops) + 0.05 * hit.weight

    def neighbours(self, token: str) -> tuple[Neighbour, ...]:
        """Corpus words reachable by a high-cosine definitional bridge."""
        if not self.lookupable(token):
            return ()
        corpus = self.corpus_words or frozenset()
        hits = self._hits(token)
        scored: list[tuple[float, Neighbour]] = []
        for word, hit in hits.items():
            if corpus and word not in corpus:
                continue
            if word == token.lower():
                continue
            if hit.gloss_cosine is None or hit.gloss_cosine < self.min_gloss_cosine:
                # Hop-1 synonym/pointer bridges may pass with a weaker centroid.
                if not (hit.hops == 1 and hit.weight >= WEIGHT_SYNONYM):
                    continue
                if hit.gloss_cosine is not None and hit.gloss_cosine < 0.5:
                    continue
            sc = self.score_hit(hit)
            if sc < self.min_score:
                continue
            scored.append((sc, Neighbour(word, float(sc), "noun_gloss_sense")))
        scored.sort(key=lambda sw: (-sw[0], sw[1].word))
        return tuple(n for _, n in scored[: self.max_neighbours])
