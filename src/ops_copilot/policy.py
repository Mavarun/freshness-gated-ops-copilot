"""Decision policy: ANSWER or a structured refusal.

Gates fire in this order:

1. session cost budget would be exceeded → REFUSE_BUDGET
   (only when use_budget_gate and a session_id is in play)
2. nothing retrieved → REFUSE_NO_EVIDENCE
3. retrieved, but no chunk actually supports the query
   (coverage below a weak floor) → REFUSE_NO_EVIDENCE
4. partial support, below the grounding threshold → REFUSE_UNGROUNDED
5. supporting chunks exist, all fail the freshness SLA → REFUSE_STALE
6. fresh supporting exists, but BM25 vs dense-stub top-k doc-ids disagree
   beyond the Jaccard threshold → REFUSE_DISAGREE
7. fresh supporting chunks fail the final answer-grounding check → REFUSE_UNGROUNDED
8. extractive draft echoes an unjustified planted canary → REFUSE_CANARY
9. else ANSWER

Freshness is applied to *supporting* evidence, not to whatever BM25 dumped.
A fresh-but-tangential Redis pool chart cannot launder a stale maxmemory-policy
runbook into an answer. When per-source SLAs are enabled, each supporting chunk
is judged against its own source_system max_age_hours.

Disagreement is checked *after* freshness and *before* grounding so a fluent
extractive draft cannot paper over ranker conflict.

Budget is checked *first* so an over-budget session cannot ANSWER even when
freshness and disagreement would otherwise pass.
"""

from __future__ import annotations

from ops_copilot.disagreement import DisagreementResult
from ops_copilot.types import (
    Chunk,
    Decision,
    FreshnessResult,
    GroundingResult,
    PolicyDecision,
)


def decide(
    retrieved: list[Chunk],
    freshness: list[FreshnessResult],
    supporting: list[Chunk],
    fresh_supporting: list[Chunk],
    grounding: GroundingResult | None,
    *,
    max_age_hours: float,
    best_support: float = 0.0,
    support_floor: float = 0.20,
    use_source_slas: bool = False,
    disagreement: DisagreementResult | None = None,
    use_disagreement_gate: bool = True,
    use_budget_gate: bool = False,
    session_spent: float = 0.0,
    request_cost: float = 0.0,
    session_budget: float = 0.0,
    session_id: str | None = None,
    canary_scan: object | None = None,
    use_canary_gate: bool = True,
) -> PolicyDecision:
    if (
        use_budget_gate
        and session_id
        and (session_spent + request_cost) > session_budget
    ):
        return PolicyDecision(
            decision=Decision.REFUSE_BUDGET,
            reason=(
                f"session cost budget exceeded "
                f"(session_id={session_id!r}; spent={session_spent:.4f}; "
                f"request_cost={request_cost:.4f}; "
                f"budget={session_budget:g}; "
                f"projected={session_spent + request_cost:.4f})"
            ),
        )

    if not retrieved:
        return PolicyDecision(
            decision=Decision.REFUSE_NO_EVIDENCE,
            reason="no retrieved chunk cleared the minimum score",
        )

    if not supporting and best_support < support_floor:
        return PolicyDecision(
            decision=Decision.REFUSE_NO_EVIDENCE,
            reason=(
                f"retrieved {len(retrieved)} chunks but none share enough "
                f"query support (best_support={best_support:.2f} < floor={support_floor:.2f})"
            ),
        )

    if not supporting:
        thresh = grounding.threshold if grounding else 0.0
        if best_support >= thresh:
            detail = (
                f"high-IDF query tokens missing from evidence "
                f"(coverage={best_support:.2f} >= {thresh:.2f} but key-token gate failed)"
            )
        else:
            detail = (
                f"retrieved evidence does not support the query "
                f"(best_support={best_support:.2f} < threshold={thresh:.2f})"
            )
        return PolicyDecision(
            decision=Decision.REFUSE_UNGROUNDED,
            reason=detail,
        )

    if not fresh_supporting:
        oldest = max((c.age_hours for c in supporting), default=0.0)
        by_id = {f.chunk_id: f for f in freshness}
        applied = []
        for chunk in supporting:
            fr = by_id.get(chunk.chunk_id)
            if fr is not None:
                applied.append(
                    f"{chunk.source_system}:{fr.max_age_hours:g}h"
                    f"(age={chunk.age_hours:.1f}h)"
                )
        sla_detail = (
            "per-source SLAs [" + "; ".join(applied[:3]) + "]"
            if use_source_slas and applied
            else f"max_age_hours={max_age_hours:g}"
        )
        return PolicyDecision(
            decision=Decision.REFUSE_STALE,
            reason=(
                f"supporting evidence fails freshness SLA "
                f"({sla_detail}; "
                f"oldest_supporting_age_hours={oldest:.1f}; "
                f"supporting={len(supporting)}; retrieved={len(retrieved)})"
            ),
        )

    if (
        use_disagreement_gate
        and disagreement is not None
        and disagreement.disagreed
    ):
        return PolicyDecision(
            decision=Decision.REFUSE_DISAGREE,
            reason=(
                f"BM25 and title-hash dense stub disagree on top-{disagreement.top_k} "
                f"doc_ids (jaccard={disagreement.jaccard:.3f} < "
                f"threshold={disagreement.threshold:g}; "
                f"bm25={list(disagreement.bm25_ids)}; "
                f"dense_stub={list(disagreement.dense_ids)})"
            ),
        )

    if grounding is None or not grounding.passed:
        cov = grounding.query_coverage if grounding else 0.0
        thresh = grounding.threshold if grounding else 0.0
        return PolicyDecision(
            decision=Decision.REFUSE_UNGROUNDED,
            reason=(
                f"fresh supporting evidence failed lexical grounding "
                f"(query_coverage={cov:.2f} < threshold={thresh:.2f})"
            ),
        )

    if (
        use_canary_gate
        and canary_scan is not None
        and getattr(canary_scan, "has_leak", False)
    ):
        n_leaked = len(getattr(canary_scan, "leaked", ()) or ())
        reg_size = int(getattr(canary_scan, "registry_size", 0) or 0)
        return PolicyDecision(
            decision=Decision.REFUSE_CANARY,
            reason=(
                f"extractive draft echoed {n_leaked} unjustified canary token(s) "
                f"(registry_size={reg_size}); token values withheld from refusal text"
            ),
        )

    cited = ", ".join(dict.fromkeys(c.doc_id for c in fresh_supporting[:3]))
    return PolicyDecision(
        decision=Decision.ANSWER,
        reason=f"fresh supporting evidence passed grounding; citing {cited}",
    )
