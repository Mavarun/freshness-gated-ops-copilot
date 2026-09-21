        return {
            "global_only": self.global_report.as_dict(),
            "per_source": self.per_source_report.as_dict(),
            "decision_flips": self.flips,
            "n_flips": len(self.flips),
        }


def load_golden(path: str | Path | None = None) -> list[dict]:
    src = Path(path) if path else DEFAULT_GOLDEN
    cases: list[dict] = []
    with src.open(encoding="utf-8") as handle:
        for line_no, raw in enumerate(handle, start=1):
            line = raw.strip()
            if not line:
                continue
            row = json.loads(line)
            missing = {"query", "expect_decision"} - set(row)
            if missing:
                raise ValueError(f"{src}:{line_no}: missing {sorted(missing)}")
            row.setdefault("note", "")
            cases.append(row)
    if len(cases) < 1:
        raise ValueError(f"golden set is empty: {src}")
    return cases


def _metrics(scores: list[CaseScore], mode: str) -> EvalReport:
    n = len(scores)
    acc = sum(1 for s in scores if s.match) / n if n else 0.0
    must = [s for s in scores if s.must_refuse]
    refused = [s for s in scores if s.did_refuse]
    tp = [s for s in refused if s.must_refuse]
    precision = (len(tp) / len(refused)) if refused else 0.0
    recall = (len(tp) / len(must)) if must else 0.0
    answered = [s for s in scores if s.actual_decision == Decision.ANSWER.value]
    grounded = [s for s in answered if s.grounding_passed]
    grind = (len(grounded) / len(answered)) if answered else 0.0
    lat = np.array([s.latency_ms for s in scores], dtype=float)
    p50 = float(np.percentile(lat, 50)) if n else 0.0
    p95 = float(np.percentile(lat, 95)) if n else 0.0
    confusion: dict[str, int] = {}
    for s in scores:
        key = f"{s.expect_decision}->{s.actual_decision}"
        confusion[key] = confusion.get(key, 0) + 1
    disagreed = [s for s in scores if s.disagreed]
    n_dis = len(disagreed)
    budgeted = [s for s in scores if s.budget_refused]
    n_bud = len(budgeted)
    canary_cases = [
        {
            "expect_canary_leak": s.expect_canary_leak,
            "actual_canary_leak": s.actual_canary_leak,
        }
        for s in scores
        if s.expect_canary_leak is not None
    ]
    canary_m = canary_detection_metrics(canary_cases)
    proposed = [s for s in scores if s.propose_write]
    n_pw = len(proposed)
    pii_cases = [
        {"expect_pii": s.expect_pii, "actual_pii": s.actual_pii}
        for s in scores
        if s.expect_pii is not None
    ]
    pii_m = pii_detection_metrics(pii_cases)
    return EvalReport(
        scores=scores,
        n=n,
        decision_accuracy=acc,
        refusal_precision=precision,
        refusal_recall=recall,
        answer_grounding_rate=grind,
        p50_latency_ms=p50,
        p95_latency_ms=p95,
        confusion=confusion,
        mode=mode,
        disagreement_rate=(n_dis / n) if n else 0.0,
        n_disagreed=n_dis,
        budget_refuse_rate=(n_bud / n) if n else 0.0,
        n_budget_refused=n_bud,
        canary_precision=float(canary_m["canary_precision"]),
        canary_recall=float(canary_m["canary_recall"]),
        canary_f1=float(canary_m["canary_f1"]),
        n_canary_labeled=int(canary_m["n_labeled"]),
        propose_write_rate=(n_pw / n) if n else 0.0,
        n_propose_write=n_pw,
        pii_precision=float(pii_m["pii_precision"]),
        pii_recall=float(pii_m["pii_recall"]),
        pii_f1=float(pii_m["pii_f1"]),
        n_pii_labeled=int(pii_m["n_labeled"]),
    )


def _expect_for_mode(case: dict, mode: str) -> str:
    if mode == "global_only":
        return str(case.get("expect_decision_global") or case["expect_decision"])
    if mode == "bm25_only":
        return str(case.get("expect_decision_bm25_only") or case["expect_decision"])
    return str(case["expect_decision"])


def run_eval(
    copilot: Copilot | None = None,
    *,
    golden_path: str | Path | None = None,
    trace_path: str | Path | None = None,
    mode: str | None = None,
) -> EvalReport:
    bot = copilot or Copilot()
    if mode is not None:
        resolved_mode = mode
    elif not bot.config.use_disagreement_gate:
        resolved_mode = "bm25_only"
    elif bot.config.use_source_slas:
        resolved_mode = "per_source"
    else:
        resolved_mode = "global_only"
    cases = load_golden(golden_path)
    tracer = TraceWriter(trace_path) if trace_path is not None else None
    if tracer:
        tracer.clear()
    scores: list[CaseScore] = []
    for case in cases:
        sid = case.get("session_id")
        if sid and "seed_session_spent" in case:
            bot.ledger.seed(str(sid), float(case["seed_session_spent"]))
        result: CopilotResult = bot.ask(
            case["query"],
            session_id=str(sid) if sid else None,
        )
        expect = _expect_for_mode(case, resolved_mode)
        actual = result.decision.value
        disagreed = None
        jaccard = None
        if result.disagreement is not None:
            disagreed = not bool(result.disagreement.get("agreed", True))
