            jaccard = result.disagreement.get("jaccard")
        score = CaseScore(
            query=case["query"],
            expect_decision=expect,
            actual_decision=actual,
            note=str(case.get("note", "")),
            match=actual == expect,
            must_refuse=_is_refuse(expect),
            did_refuse=_is_refuse(actual),
            latency_ms=result.latency_ms,
            grounding_passed=None if result.grounding is None else result.grounding.passed,
            cited_ids=result.cited_ids,
            reason=result.reason,
            mode=resolved_mode,
            disagreed=disagreed,
            jaccard=jaccard,
            session_id=str(sid) if sid else None,
            budget_refused=actual == Decision.REFUSE_BUDGET.value,
        )
        scores.append(score)
        if tracer:
            tracer.write(
                result,
                extra={
                    "expect_decision": expect,
                    "match": score.match,
                    "note": score.note,
                    "mode": resolved_mode,
                },
            )
    return _metrics(scores, resolved_mode)


def run_comparison(
    *,
    golden_path: str | Path | None = None,
    corpus_path: str | Path | None = None,
    trace_path: str | Path | None = None,
) -> ComparisonReport:
    """Run the golden set twice: global-only SLA vs per-source SLAs."""
    shared_kwargs: dict = {}
    if corpus_path is not None:
        shared_kwargs["path"] = corpus_path

    global_bot = Copilot(
        config=CopilotConfig(use_source_slas=False, max_age_hours=48.0),
        **shared_kwargs,
    )
    per_bot = Copilot(
        config=CopilotConfig(use_source_slas=True, max_age_hours=48.0),
        **shared_kwargs,
    )

    global_report = run_eval(
        global_bot,
        golden_path=golden_path,
        mode="global_only",
    )
    per_report = run_eval(
        per_bot,
        golden_path=golden_path,
        trace_path=trace_path,
        mode="per_source",
    )

    flips: list[dict] = []
    for g, p in zip(global_report.scores, per_report.scores, strict=True):
        if g.actual_decision != p.actual_decision:
            flips.append(
                {
                    "query": g.query,
                    "global_decision": g.actual_decision,
                    "per_source_decision": p.actual_decision,
                    "note": p.note or g.note,
                }
            )
    return ComparisonReport(
        global_report=global_report,
        per_source_report=per_report,
        flips=flips,
    )


def render_markdown(report: EvalReport) -> str:
    m = report.as_dict()
    lines = [
        "# Freshness-gated ops copilot - golden eval",
        "",
        "## Summary metrics",
        "",
        "| Metric | Value |",
        "| --- | ---: |",
        f"| mode | {m['mode']} |",
        f"| cases | {m['n']} |",
        f"| decision_accuracy | {m['decision_accuracy']:.3f} |",
        f"| refusal_precision | {m['refusal_precision']:.3f} |",
        f"| refusal_recall | {m['refusal_recall']:.3f} |",
        f"| answer_grounding_rate | {m['answer_grounding_rate']:.3f} |",
        f"| disagreement_rate | {m.get('disagreement_rate', 0.0):.3f} |",
        f"| n_disagreed | {m.get('n_disagreed', 0)} |",
        f"| budget_refuse_rate | {m.get('budget_refuse_rate', 0.0):.3f} |",
        f"| n_budget_refused | {m.get('n_budget_refused', 0)} |",
        f"| p50_latency_ms | {m['p50_latency_ms']:.2f} |",
        f"| p95_latency_ms | {m['p95_latency_ms']:.2f} |",
        "",
    ]
    return "\n".join(lines)


def render_comparison_markdown(comparison: ComparisonReport) -> str:
    return render_markdown(comparison.per_source_report)
