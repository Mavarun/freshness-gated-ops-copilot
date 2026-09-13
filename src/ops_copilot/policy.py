"""Decision policy: ANSWER or a structured refusal.

Gates fire in this order:

1. nothing retrieved → REFUSE_NO_EVIDENCE
2. retrieved, but no chunk actually supports the query
   (coverage below a weak floor) → REFUSE_NO_EVIDENCE
3. partial support, below the grounding threshold → REFUSE_UNGROUNDED
4. supporting chunks exist, all fail the freshness SLA → REFUSE_STALE
5. fresh supporting chunks fail the final answer-grounding check → REFUSE_UNGROUNDED
6. else ANSWER

Freshness is applied to *supporting* evidence, not to whatever BM25 dumped.
A fresh-but-tangential Redis pool chart cannot launder a stale maxmemory-policy
runbook into an answer. When per-source SLAs are enabled, each supporting chunk
is judged against its own source_system max_age_hours.
"""

from __future__ import annotations

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
) -> PolicyDecision:
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
        # Prefer the SLA that was actually applied to supporting evidence.
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

    cited = ", ".join(dict.fromkeys(c.doc_id for c in fresh_supporting[:3]))
    return PolicyDecision(
        decision=Decision.ANSWER,
        reason=f"fresh supporting evidence passed grounding; citing {cited}",
    )
