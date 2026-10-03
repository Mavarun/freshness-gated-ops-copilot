"""Structured, actionable refusal explanations.

A refusal used to carry one free-text ``reason``. Every refusal decision
now also carries an ``explanation`` (``RefusalExplanation.as_dict()``) built
by the policy branch that refused, so it always names the gate that fired:

- ``gate`` / ``decision`` / ``summary``;
- ``evidence_doc_ids``: the documents the verdict is about (stale
  supporting docs, the closest doc for ungrounded, the two disagreeing top
  docs, the docs holding a leaked canary or secret, the rotation page for a
  page without a recipient);
- ``stale_sources`` (REFUSE_STALE): per supporting document, in retrieval
  rank order, its source system, age, SLA, how far over it is, and its
  ``updated_at``;
- ``missing_terms`` (REFUSE_UNGROUNDED / REFUSE_NO_EVIDENCE): salient query
  terms the closest evidence does not support, key terms first;
- ``top_doc_ids`` (REFUSE_DISAGREE): BM25's and the dense retriever's top doc;
- ``write`` (REFUSE_AMBIGUOUS_WRITE): reason code, parsed action / verb /
  target and did-you-mean suggestions;
- ``details``: gate-specific numbers (budget, counts, kinds);
- ``remediation``: what to do about it, as ``{action, target, text}``
  ("refresh_source", "add_runbook", "reconcile_sources", "name_target" ...).

Explanations are built only from doc ids, source systems, numbers, registry
names, ontology words and salient query terms, never from evidence text, and
are passed through ``explain_redact`` before they leave the pipeline (canary
tokens, PII and secret-shaped strings never appear in one).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Iterable, Sequence

from ops_copilot.explain_redact import redact_explanation
from ops_copilot.types import Chunk, Decision, FreshnessResult

GATE_BY_DECISION: dict[Decision, str] = {
    Decision.REFUSE_BUDGET: "budget",
    Decision.REFUSE_AMBIGUOUS_WRITE: "write_ambiguity",
    Decision.REFUSE_NO_EVIDENCE: "evidence",
    Decision.REFUSE_UNGROUNDED: "grounding",
    Decision.REFUSE_STALE: "freshness",
    Decision.REFUSE_DISAGREE: "disagreement",
    Decision.REFUSE_CANARY: "canary",
    Decision.REFUSE_PII: "pii",
}
REFUSALS = frozenset(GATE_BY_DECISION)

WRITE_REASON_CODES: dict[str, str] = {
    "no_target": "the action names no target",
    "unregistered_target": "the target is not in the corpus registry",
    "no_recipient": "the page names nobody to wake",
    "several_targets": "more than one target",
    "several_actions": "more than one action",
    "conditional": "the instruction depends on a condition",
    "unsupported_verb": "no action exists for this mutation",
    "unknown_verb": "the verb is not a recognised action",
    "kind_mismatch": "the action does not take this kind of target",
    "low_confidence": "the parse is not confident enough",
}


@dataclass(frozen=True)
class Remediation:
    action: str
    target: str | None
    text: str

    def as_dict(self) -> dict[str, Any]:
        return {"action": self.action, "target": self.target, "text": self.text}


@dataclass
class RefusalExplanation:
    decision: str
    gate: str
    summary: str
    evidence_doc_ids: list[str] = field(default_factory=list)
    stale_sources: list[dict[str, Any]] = field(default_factory=list)
    missing_terms: list[str] = field(default_factory=list)
    top_doc_ids: dict[str, Any] | None = None
    write: dict[str, Any] | None = None
    details: dict[str, Any] = field(default_factory=dict)
    remediation: list[Remediation] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return {
            "decision": self.decision,
            "gate": self.gate,
            "summary": self.summary,
            "evidence_doc_ids": list(self.evidence_doc_ids),
            "stale_sources": [dict(s) for s in self.stale_sources],
            "missing_terms": list(self.missing_terms),
            "top_doc_ids": dict(self.top_doc_ids) if self.top_doc_ids else None,
            "write": dict(self.write) if self.write else None,
            "details": dict(self.details),
            "remediation": [r.as_dict() for r in self.remediation],
        }


@dataclass
class GroundingGap:
    """Closest evidence for an unsupported query and the terms it lacks."""

    closest_doc_id: str | None
    missing_terms: list[str]
    coverage: float = 0.0


@dataclass
class ExplainContext:
    """What the pipeline knows beyond the policy's own inputs.

    The two grounding gaps can be given as values or as zero-argument
    callables; a callable runs only if a grounding / evidence refusal needs it,
    so an ANSWER never pays for its explanation.
    """

    gap_fn: Callable[[], GroundingGap | None] | GroundingGap | None = None  # vs the best retrieved chunk
    answer_gap_fn: Callable[[], GroundingGap | None] | GroundingGap | None = None  # vs the fresh evidence
    canary_doc_ids: list[str] = field(default_factory=list)
    pii_doc_ids: list[str] = field(default_factory=list)
    registry: Any = None  # write_targets.EntityRegistry
    query: str = ""  # raw query; its sensitive spans seed the redaction pass

    @staticmethod
    def _resolve(v: Any) -> GroundingGap | None:
        return v() if callable(v) else v

    @property
    def gap(self) -> GroundingGap | None:
        return self._resolve(self.gap_fn)

    @property
    def answer_gap(self) -> GroundingGap | None:
        return self._resolve(self.answer_gap_fn)


def _uniq(ids: Iterable[str | None]) -> list[str]:
    return [i for i in dict.fromkeys(ids) if i]


def _terms(terms: list[str], n: int = 3) -> str:
    return ", ".join(repr(t) for t in terms[:n])


# --- per gate ----------------------------------------------------------------


def explain_budget(session_id: str | None, spent: float, cost: float, budget: float) -> RefusalExplanation:
    projected = spent + cost
    return RefusalExplanation(
        Decision.REFUSE_BUDGET.value, "budget",
        f"session would spend {projected:.2f} of a {budget:g}-unit budget",
        details={
            "session_spent": round(spent, 4),
            "request_cost": round(cost, 4),
            "session_budget": budget,
            "projected": round(projected, 4),
        },
        remediation=[
            Remediation("start_new_session", None, "Start a new session, or ask an operator to raise session_budget_cost_units."),
        ],
    )


def explain_no_evidence(
    retrieved: list[Chunk], gap: GroundingGap | None, *, best_support: float, floor: float
) -> RefusalExplanation:
    missing = list(gap.missing_terms) if gap else []
    closest = gap.closest_doc_id if gap and retrieved else None
    if not retrieved:
        summary = "no document cleared the retrieval score floor"
    else:
        summary = f"closest document {closest} covers {best_support:.2f} of the query (floor {floor:.2f})"
    topic = _terms(missing) or "this question"
    return RefusalExplanation(
        Decision.REFUSE_NO_EVIDENCE.value, "evidence", summary,
        evidence_doc_ids=_uniq([closest]),
        missing_terms=missing,
        details={"n_retrieved": len(retrieved), "best_support": round(best_support, 4), "support_floor": floor},
        remediation=[
            Remediation(
                "add_runbook", " ".join(missing[:3]) or None,
                f"No document covers {topic}; add a runbook or doc for it.",
            )
        ],
    )


def explain_ungrounded(gap: GroundingGap | None, *, coverage: float, threshold: float, stage: str) -> RefusalExplanation:
    missing = list(gap.missing_terms) if gap else []
    closest = gap.closest_doc_id if gap else None
    topic = _terms(missing) or "the question's key terms"
    where = f"closest document {closest}" if closest else "the evidence"
    summary = f"{where} does not mention {topic} (coverage {coverage:.2f} vs {threshold:.2f})"
    rem = [
        Remediation(
            "add_runbook", " ".join(missing[:3]) or None,
            f"Add a runbook for {topic}, or extend {closest} to cover it." if closest
            else f"Add a runbook for {topic}.",
        ),
        Remediation("rephrase", None, "If the question is about what that document does say, rephrase with its terms."),
    ]
    return RefusalExplanation(
        Decision.REFUSE_UNGROUNDED.value, "grounding", summary,
        evidence_doc_ids=_uniq([closest]),
        missing_terms=missing,
        details={"stage": stage, "coverage": round(coverage, 4), "threshold": threshold},
        remediation=rem,
    )


def explain_stale(supporting: list[Chunk], freshness: list[FreshnessResult]) -> RefusalExplanation:
    by_id = {f.chunk_id: f for f in freshness}
    rows: dict[str, dict[str, Any]] = {}
    for chunk in supporting:
        fr = by_id.get(chunk.chunk_id)
        sla = float(fr.max_age_hours) if fr is not None else None
        prev = rows.get(chunk.doc_id)
        if prev is not None:
            continue
        rows[chunk.doc_id] = {
            "doc_id": chunk.doc_id,
            "source_system": chunk.source_system,
            "updated_at": chunk.updated_at.isoformat(),
            "age_hours": round(chunk.age_hours, 1),
            "sla_hours": sla,
            "over_by_hours": None if sla is None else round(chunk.age_hours - sla, 1),
        }
    stale = list(rows.values())  # retrieval rank order: most relevant stale doc first
    head = stale[0] if stale else None
    summary = (
        f"{head['doc_id']} ({head['source_system']}) is {head['age_hours']:.1f}h old vs a {head['sla_hours']:g}h SLA"
        if head
        else "supporting evidence fails its freshness SLA"
    )
    if len(stale) > 1:
        summary += f" (+{len(stale) - 1} more stale doc{'s' if len(stale) > 2 else ''})"
    return RefusalExplanation(
        Decision.REFUSE_STALE.value, "freshness", summary,
        evidence_doc_ids=[r["doc_id"] for r in stale],
        stale_sources=stale,
        remediation=[
            Remediation(
                "refresh_source", r["doc_id"],
                f"Refresh {r['doc_id']} ({r['source_system']}): {r['age_hours']:.1f}h old, "
                f"SLA {r['sla_hours']:g}h.",
            )
            for r in stale
        ],
    )


def explain_disagree(disagreement: Any) -> RefusalExplanation:
    bm25 = list(getattr(disagreement, "bm25_ids", ()) or ())
    dense = list(getattr(disagreement, "dense_ids", ()) or ())
    name = getattr(disagreement, "dense_name", "dense")
    a, b = (bm25[0] if bm25 else None), (dense[0] if dense else None)
    return RefusalExplanation(
        Decision.REFUSE_DISAGREE.value, "disagreement",
        f"BM25 ranks {a} first, {name} ranks {b} first",
        evidence_doc_ids=_uniq([a, b]),
        top_doc_ids={
            "bm25": a,
            "dense": b,
            "dense_retriever": name,
            "jaccard": round(float(getattr(disagreement, "jaccard", 0.0)), 4),
            "threshold": getattr(disagreement, "threshold", None),
        },
        remediation=[
            Remediation(
                "reconcile_sources", " vs ".join(_uniq([a, b])) or None,
                f"Check whether {a} or {b} answers this; retitle, merge or retire the other so both rankers agree, "
                "or rephrase with an exact identifier.",
            )
        ],
    )


def explain_canary(scan: Any, doc_ids: list[str]) -> RefusalExplanation:
    n = len(getattr(scan, "leaked", ()) or ())
    return RefusalExplanation(
        Decision.REFUSE_CANARY.value, "canary",
        f"the draft echoed {n} planted canary token(s) the query did not ask for (values withheld)",
        evidence_doc_ids=list(doc_ids),
        details={"n_leaked": n, "registry_size": int(getattr(scan, "registry_size", 0) or 0)},
        remediation=[
            Remediation(
                "quarantine_doc", d,
                f"Quarantine {d} or strip the injected token from it; it reached an answer draft.",
            )
            for d in doc_ids
        ] or [Remediation("quarantine_doc", None, "Quarantine the document that carries the canary token.")],
    )


def explain_pii(scan: Any, doc_ids: list[str]) -> RefusalExplanation:
    kinds = sorted({getattr(m, "kind", "?") for m in (getattr(scan, "matches", ()) or ())})
    quarantined = sorted(getattr(scan, "evidence_secret_kinds", ()) or ())
    all_kinds = sorted(set(kinds) | set(quarantined)) or ["pii"]
    rem = [
        Remediation(
            "scrub_secret", d,
            f"Move the {'/'.join(all_kinds)} out of {d} (secret store or masked contact); values withheld.",
        )
        for d in doc_ids
    ]
    if "email" in all_kinds:
        rem.append(Remediation("rephrase", None, "Ask for the rotation contact email explicitly to get a masked contact."))
    return RefusalExplanation(
        Decision.REFUSE_PII.value, "pii",
        f"the answer would expose {'/'.join(all_kinds)} (values withheld)",
        evidence_doc_ids=list(doc_ids),
        details={"kinds": kinds, "evidence_secret_kinds": quarantined, "n_matches": int(getattr(scan, "redactions_count", 0) or 0)},
        remediation=rem or [Remediation("scrub_secret", None, "Remove the secret from the cited document.")],
    )


def _supported_actions(kind: str | None) -> list[str]:
    from ops_copilot.write_ontology import ONTOLOGY

    return [s.anchor for s in ONTOLOGY if kind is None or kind in s.target_kinds]


def explain_ambiguous_write(intent: Any, registry: Any = None) -> RefusalExplanation:
    from ops_copilot.write_ontology import SPEC_BY_ACTION

    code = getattr(intent, "reason_code", "") or "low_confidence"
    action = getattr(intent, "action", None)
    target = getattr(intent, "target", None)
    verb = getattr(intent, "verb", "") or None
    sugg = list(getattr(intent, "suggestions", []) or [])
    payload = dict(getattr(intent, "payload", {}) or {})
    spec = SPEC_BY_ACTION.get(action) if action is not None else None
    anchor = spec.anchor if spec else (verb or "restart")
    kinds = spec.target_kinds if spec else ()
    tname = getattr(target, "name", None)
    tkind = getattr(target, "kind", None)
    rem: list[Remediation] = []
    if code in ("unregistered_target", "no_target"):
        if sugg:
            rem += [Remediation("name_target", s, f"Did you mean {s}? Restate as '{anchor} {s}'.") for s in sugg]
        else:
            known = []
            if registry is not None:
                known = [n for k in kinds[:1] for n in registry.names(k)][:5]
            noun = kinds[0].replace("_", " ") if kinds else "target"
            rem.append(
                Remediation(
                    "name_target", None,
                    f"Name one registered {noun}" + (f" (for example {', '.join(known)})." if known else "."),
                )
            )
    elif code == "no_recipient":
        for s in sugg:
            rem.append(Remediation("name_recipient", s, f"Name who to page, for example '{anchor} {s}'."))
        if not sugg:
            rem.append(Remediation("name_recipient", None, "Name who to page (a registered pager)."))
        if payload.get("rotation_doc") and "stale" in getattr(intent, "reason", ""):
            doc = payload["rotation_doc"]
            rem.append(Remediation("refresh_source", doc, f"Refresh the on-call rotation page {doc}; it is past its SLA."))
    elif code in ("several_targets", "several_actions"):
        rem.append(Remediation("restate_one_action", None, "Ask for one action on one target per request."))
    elif code == "conditional":
        rem.append(Remediation("restate_without_condition", None, "Ask again as a plain instruction once the condition holds."))
    elif code in ("unsupported_verb", "unknown_verb", "kind_mismatch"):
        acts = _supported_actions(tkind)
        what = f"{tname} ({tkind})" if tname else "this target"
        rem.append(
            Remediation(
                "use_supported_action", tname,
                f"{verb!r} is not an action here; for {what} say one of: {', '.join(acts)}." if code != "kind_mismatch"
                else f"{anchor!r} does not take a {tkind}; for {what} say one of: {', '.join(acts)}.",
            )
        )
    else:
        rem.append(Remediation("rephrase", None, "Restate as one explicit action and a registered target."))
    docs = _uniq([payload.get("rotation_doc")])
    return RefusalExplanation(
        Decision.REFUSE_AMBIGUOUS_WRITE.value, "write_ambiguity",
        f"not proposed: {WRITE_REASON_CODES.get(code, code)}",
        evidence_doc_ids=docs,
        write={
            "reason_code": code,
            "action": getattr(action, "value", None),
            "verb": verb,
            "target": tname,
            "target_kind": tkind,
            "suggestions": sugg,
        },
        remediation=rem,
    )


def finalize(expl: RefusalExplanation | None, *, context: Sequence[str] = ()) -> dict[str, Any] | None:
    """Serialize and redact (see ``explain_redact``); ``context`` is the raw query."""
    if expl is None:
        return None
    out, _ = redact_explanation(expl.as_dict(), context=context)
    return out
