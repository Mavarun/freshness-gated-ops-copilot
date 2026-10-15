"""Ops gloss-sense model: definitional bridges from Wiktionary computing senses.

Not a synonym table. Lexical backoffs tried so far (counter-fitted vectors,
tag synonyms, Wiktionary *gloss heads*, Q&A translation, passage support)
either look up a fixed substitute list or score whole passages. Hard pairs
such as ``bounce~restart`` (domain-vector cosine 0.08 — email sense) stay
apart because the *wrong sense* dominates the global vector.

This module reads the *full gloss* of each computing sense and builds a
small definitional graph over verb senses:

- listed synonym <-> headword (weight 2, bidirectional);
- pointer gloss ("Synonym of X") <-> X (weight 2);
- every alphabetic gloss content word that is itself a computing *verb*
  headword <-> headword (weight 1).

A query verb reaches an ontology verb when a short path exists (default
max 2 hops). ``bounce`` reaches ``reboot`` in one gloss hop and
``restart`` in two (via restart's synonym-of-reboot pointer), which is
exactly the ops sense the global vector missed.

Paths are ranked by hop distance, cumulative edge weight, and the cosine
of domain-vector *gloss centroids* (mean of the sense's gloss-token
vectors). Target-kind compatibility gates which ontology actions may win.

The write path (``match_action``) only upgrades an instruction shaped
``<unknown verb> [the] <entity>`` from ambiguous to propose when the best
compatible action clears a calibrated threshold and margin. Grounding
(``neighbours``) exposes corpus words reachable the same way.

Calibrated on clean golden + *dev* synonym rows only. Held-out words may
appear in the external Wiktionary extract (editors never saw this eval);
they are never hand-authored into product lexicons. Ships off by default
until a held-out run meets the pre-registered go / no-go rule.
"""

from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass
from functools import lru_cache
from typing import Iterable

import numpy as np

from ops_copilot.domain_vectors import DomainVectors, default_vectors
from ops_copilot.semantic import Neighbour
from ops_copilot.text import content_tokens, fold_token, is_identifier, normalize_text
from ops_copilot.wiktionary_senses import load_extract
from ops_copilot.write_ontology import (
    SPEC_BY_ACTION,
    WriteActionType,
    action_verbs,
    verb_index,
)

MIN_WORD_LEN = 3
WEIGHT_SYNONYM = 2
WEIGHT_GLOSS = 1
DEFAULT_MAX_HOPS = 2
DEFAULT_MIN_SCORE = 3.0
DEFAULT_MARGIN = 0.4
DEFAULT_MIN_GLOSS_COSINE = 0.5


def _verb_senses() -> list[dict]:
    return [s for s in load_extract()["senses"] if s.get("pos") == "verb"]


@lru_cache(maxsize=1)
def verb_headwords() -> frozenset[str]:
    return frozenset(s["word"] for s in _verb_senses() if len(s["word"]) >= MIN_WORD_LEN)


def gloss_tokens(gloss: str) -> list[str]:
    """Alphabetic content tokens of a gloss (pointer prefixes stripped lightly)."""
    text = normalize_text(gloss)
    for pre in ("synonym of ", "alternative form of ", "see "):
        if text.startswith(pre):
            text = text[len(pre) :]
            break
    return [t for t in content_tokens(text) if t.isalpha() and len(t) >= MIN_WORD_LEN]


@dataclass(frozen=True)
class SenseEdge:
    left: str
    right: str
    weight: int
    kind: str  # synonym | pointer | gloss


@lru_cache(maxsize=1)
def build_verb_graph() -> dict[str, list[tuple[str, int, str]]]:
    """Undirected verb-sense graph: word -> [(neighbour, weight, kind), ...]."""
    heads = verb_headwords()
    adj: dict[str, dict[str, tuple[int, str]]] = defaultdict(dict)

    def link(a: str, b: str, weight: int, kind: str) -> None:
        if a == b or len(a) < MIN_WORD_LEN or len(b) < MIN_WORD_LEN:
            return
        for x, y in ((a, b), (b, a)):
            prev = adj[x].get(y)
            if prev is None or weight > prev[0]:
                adj[x][y] = (weight, kind)

    for s in _verb_senses():
        h = s["word"]
        gloss = s.get("gloss") or ""
        text = normalize_text(gloss)
        pointer = any(text.startswith(p) for p in ("synonym of ", "alternative form of "))
        for syn in s.get("synonyms") or []:
            if isinstance(syn, str) and syn.isalpha():
                link(h, syn.lower(), WEIGHT_SYNONYM, "synonym")
        toks = gloss_tokens(gloss)
        if pointer and toks:
            link(h, toks[0], WEIGHT_SYNONYM, "pointer")
        for tok in toks:
            if tok in heads:
                link(h, tok, WEIGHT_GLOSS, "gloss")
    return {
        w: [(n, wt, kind) for n, (wt, kind) in sorted(nbrs.items())]
        for w, nbrs in sorted(adj.items())
    }


def gloss_centroid(word: str, vectors: DomainVectors | None = None) -> np.ndarray | None:
    """Mean domain vector of the word's verb-sense gloss tokens (and synonyms)."""
    dv = vectors if vectors is not None else default_vectors()
    toks: list[str] = []
    for s in _verb_senses():
        if s["word"] != word:
            continue
        toks.extend(gloss_tokens(s.get("gloss") or ""))
        toks.extend(
            syn.lower()
            for syn in (s.get("synonyms") or [])
            if isinstance(syn, str) and syn.isalpha()
        )
    vecs = [dv.vector(t) for t in toks if t != word and dv.vector(t) is not None]
    if not vecs:
        # Fall back to the word's own vector when it has a sense but empty gloss vec.
        own = dv.vector(word)
        return None if own is None else own.astype(np.float64)
    v = np.mean(np.stack(vecs), axis=0)
    n = float(np.linalg.norm(v))
    return v / n if n > 0 else None


def gloss_cosine(a: str, b: str, vectors: DomainVectors | None = None) -> float | None:
    va, vb = gloss_centroid(a, vectors), gloss_centroid(b, vectors)
    if va is None or vb is None:
        return None
    return float(va @ vb)


@dataclass(frozen=True)
class BridgeHit:
    word: str
    hops: int
    weight: float  # sum of edge weights along best path
    path: tuple[str, ...]
    gloss_cosine: float | None


def bridges_from(
    start: str,
    *,
    max_hops: int = DEFAULT_MAX_HOPS,
    vectors: DomainVectors | None = None,
) -> dict[str, BridgeHit]:
    """Shortest-path definitional bridges from ``start`` (by hops, then -weight)."""
    graph = build_verb_graph()
    tok = start.lower()
    if tok not in graph and fold_token(tok) in graph:
        tok = fold_token(tok)
    if tok not in graph:
        return {}
    # state: word -> (hops, weight, parent)
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
            gloss_cosine=gloss_cosine(tok, word, dv),
        )
    return hits


def _action_for_verb(verb: str) -> WriteActionType | None:
    acts = verb_index().get(verb)
    return acts[0] if acts else None


@dataclass
class GlossSenseBackoff:
    """Definitional-sense backoff for write verbs and grounding substitutes."""

    max_hops: int = DEFAULT_MAX_HOPS
    min_score: float = DEFAULT_MIN_SCORE
    margin: float = DEFAULT_MARGIN
    min_gloss_cosine: float = DEFAULT_MIN_GLOSS_COSINE
    max_neighbours: int = 2
    corpus_words: frozenset[str] | None = None

    def __post_init__(self) -> None:
        self._vectors = default_vectors()
        self._ontology = frozenset(action_verbs())
        self._cache: dict[str, dict[str, BridgeHit]] = {}

    def _hits(self, token: str) -> dict[str, BridgeHit]:
        tok = token.lower()
        if tok not in self._cache:
            self._cache[tok] = bridges_from(tok, max_hops=self.max_hops, vectors=self._vectors)
        return self._cache[tok]

    @staticmethod
    def lookupable(token: str) -> bool:
        return (
            token.isalpha()
            and not is_identifier(token)
            and len(token) >= MIN_WORD_LEN
        )

    def score_hit(self, hit: BridgeHit) -> float:
        """Higher is better: prefer short, heavy paths with aligned gloss centroids."""
        cos = hit.gloss_cosine if hit.gloss_cosine is not None else 0.0
        # hops 1 -> 2.0 bonus, hops 2 -> 1.0; weight typically 1-4
        return (3 - hit.hops) + 0.5 * hit.weight + cos

    def match_action(self, verb: str, target_kind: str) -> dict | None:
        """Nearest compatible ontology action for an unknown write verb, or None."""
        if not self.lookupable(verb):
            return None
        hits = self._hits(verb)
        # Collect best score per action among reachable ontology verbs.
        per_action: dict[str, tuple[float, BridgeHit, str]] = {}
        for word, hit in hits.items():
            action = _action_for_verb(word)
            if action is None:
                continue
            spec = SPEC_BY_ACTION[action]
            if target_kind not in spec.target_kinds and target_kind != "unknown":
                continue
            if hit.gloss_cosine is not None and hit.gloss_cosine < self.min_gloss_cosine:
                # Allow hop-1 synonym/pointer bridges even with a weak centroid.
                if not (hit.hops == 1 and hit.weight >= WEIGHT_SYNONYM):
                    continue
            sc = self.score_hit(hit)
            prev = per_action.get(action.value)
            if prev is None or sc > prev[0]:
                per_action[action.value] = (sc, hit, word)

        if not per_action:
            return {
                "accepted": False,
                "action": None,
                "verb": verb,
                "score": 0.0,
                "margin": 0.0,
                "why": "no definitional bridge to a compatible ontology verb",
                "source": "gloss_sense",
            }
        ranked = sorted(per_action.items(), key=lambda kv: -kv[1][0])
        best_action, (best_score, best_hit, best_verb) = ranked[0]
        second = ranked[1][1][0] if len(ranked) > 1 else 0.0
        gap = best_score - second
        accepted = best_score >= self.min_score and gap >= self.margin
        why = "accepted" if accepted else (
            f"score {best_score:.2f} < {self.min_score}" if best_score < self.min_score
            else f"margin {gap:.2f} < {self.margin}"
        )
        return {
            "accepted": accepted,
            "action": best_action,
            "verb": verb,
            "bridged_verb": best_verb,
            "score": round(best_score, 4),
            "margin": round(gap, 4),
            "hops": best_hit.hops,
            "path": list(best_hit.path),
            "gloss_cosine": None if best_hit.gloss_cosine is None else round(best_hit.gloss_cosine, 4),
            "confidence": min(1.0, 0.7 + 0.1 * best_hit.weight / best_hit.hops),
            "why": why,
            "source": "gloss_sense",
            "runners_up": [
                {"action": a, "score": round(s, 4), "bridged_verb": v}
                for a, (s, _h, v) in ranked[1:3]
            ],
        }

    def neighbours(self, token: str) -> tuple[Neighbour, ...]:
        """Corpus words reachable by a definitional bridge (for grounding)."""
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
            if hit.gloss_cosine is not None and hit.gloss_cosine < self.min_gloss_cosine:
                if not (hit.hops == 1 and hit.weight >= WEIGHT_SYNONYM):
                    continue
            sc = self.score_hit(hit)
            if sc < self.min_score:
                continue
            scored.append((sc, Neighbour(word, float(sc), "gloss_sense")))
        scored.sort(key=lambda sw: (-sw[0], sw[1].word))
        return tuple(n for _, n in scored[: self.max_neighbours])
