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
