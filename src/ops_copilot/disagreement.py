"""Retriever disagreement: Jaccard overlap on top-k doc-id sets.

BM25 and a second dense stub often disagree on which evidence is best.
When their top-k doc-id sets fall below a Jaccard threshold, the policy can
REFUSE_DISAGREE even if freshness and grounding would otherwise pass —
reducing silent wrong answers from a single brittle ranker.
"""

from __future__ import annotations

from dataclasses import dataclass

from ops_copilot.types import Chunk


def jaccard(ids_a: set[str], ids_b: set[str]) -> float:
    """Jaccard index |A∩B| / |A∪B|; empty∪empty → 1.0 (vacuous agreement)."""
    if not ids_a and not ids_b:
        return 1.0
    union = ids_a | ids_b
    if not union:
        return 1.0
    return len(ids_a & ids_b) / len(union)


def doc_id_set(hits: list[Chunk], *, top_k: int) -> set[str]:
    """Unique doc_ids in rank order, truncated to ``top_k``."""
    ids: list[str] = []
    for hit in hits:
        if hit.doc_id not in ids:
            ids.append(hit.doc_id)
        if len(ids) >= top_k:
            break
    return set(ids)


@dataclass(frozen=True)
class DisagreementResult:
    """Outcome of comparing two retrievers' top-k doc-id sets."""

    jaccard: float
    threshold: float
    top_k: int
    bm25_ids: tuple[str, ...]
    dense_ids: tuple[str, ...]
    agreed: bool

    @property
    def disagreed(self) -> bool:
        return not self.agreed

    def as_dict(self) -> dict:
        return {
            "jaccard": round(self.jaccard, 4),
            "threshold": self.threshold,
            "top_k": self.top_k,
            "bm25_ids": list(self.bm25_ids),
            "dense_ids": list(self.dense_ids),
            "agreed": self.agreed,
        }


def assess_disagreement(
    bm25_hits: list[Chunk],
    dense_hits: list[Chunk],
    *,
    top_k: int = 1,
    threshold: float = 1.0,
) -> DisagreementResult:
    """Compare top-k doc-id sets; ``agreed`` when Jaccard >= threshold.

    Default ``top_k=1`` and ``threshold=1.0`` require identical top evidence
    (Jaccard of singletons is 0 or 1). Larger ``top_k`` with a softer threshold
    allows partial overlap before refusing.
    """
    bm25_ordered: list[str] = []
    for hit in bm25_hits:
        if hit.doc_id not in bm25_ordered:
            bm25_ordered.append(hit.doc_id)
        if len(bm25_ordered) >= top_k:
            break
    dense_ordered: list[str] = []
    for hit in dense_hits:
        if hit.doc_id not in dense_ordered:
            dense_ordered.append(hit.doc_id)
        if len(dense_ordered) >= top_k:
            break

    a = set(bm25_ordered)
    b = set(dense_ordered)
    score = jaccard(a, b)
    return DisagreementResult(
        jaccard=score,
        threshold=threshold,
        top_k=top_k,
        bm25_ids=tuple(bm25_ordered),
        dense_ids=tuple(dense_ordered),
        agreed=score >= threshold,
    )
