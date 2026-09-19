# Freshness-gated ops copilot

Ops knowledge copilot that refuses when evidence fails a freshness SLA, grounding
check, retriever-agreement check, or **session cost budget**. Offline CI, frozen clock.

| Decision | Meaning |
| --- | --- |
| `ANSWER` | Fresh supporting evidence passed grounding |
| `REFUSE_STALE` | Supporting chunks older than the SLA |
| `REFUSE_UNGROUNDED` | Related retrieval does not support the ask |
| `REFUSE_NO_EVIDENCE` | Nothing in the corpus matches |
| `REFUSE_DISAGREE` | BM25 and title-hash dense stub disagree on top-k |
| `REFUSE_BUDGET` | Session spent + request `approx_cost_units` would exceed session budget |

## Hypothesis (2026-09-20 session cost budget)

1. Production agents need a hard session cost budget; exceeding it must `REFUSE_BUDGET` **before answering**.
2. Traces already carry `approx_cost_units` — accumulate per `session_id` and gate in policy.
3. Golden + API tests prove budget trips **independently** of freshness/disagreement.

Prior (2026-09-16): disagreement routing. Prior (2026-09-15): FastAPI. Prior (2026-09-14): per-source SLAs.

## Architecture (budget first)

```
query (+ optional session_id)
  -> budget gate (REFUSE_BUDGET if spent + cost > budget)
  -> retrieve BM25 + TitleHashDenseStub
  -> support / freshness / disagreement / grounding
  -> ANSWER | REFUSE_*
  -> record cost on session ledger
```

Defaults: `use_budget_gate=True`, `session_budget_cost_units=5.0` (approx 2 answers then refuse).

## Package

```
src/ops_copilot/
  cost_budget.py     SessionCostLedger (spent/record/seed/would_exceed)
  policy.py          REFUSE_BUDGET checked first when session_id present
  pipeline.py        ask(..., session_id=); ledger accumulation
  eval.py            golden seeds + budget_refuse_rate / n_budget_refused
  api.py             optional session_id body or X-Session-Id header
```

## How to run

```bash
python -m pip install -e ".[dev,api]"
pytest
python scripts/run_eval.py
python scripts/run_api.py
# curl POST /query — optional session_id / X-Session-Id; REFUSE_BUDGET when over budget
```

## Golden eval (real run — 2026-09-20)

35 labeled cases on frozen clock `2026-09-13T00:00:00+00:00`.

| Metric | Per-source + disagreement + budget |
| --- | ---: |
| cases | 35 |
| decision_accuracy | 1.000 |
| refusal_precision | 1.000 |
| refusal_recall | 1.000 |
| answer_grounding_rate | 1.000 |
| disagreement_rate | 0.314 |
| n_disagreed | 11 |
| budget_refuse_rate | 0.086 |
| n_budget_refused | 3 |

**Budget independence:** three `REFUSE_BUDGET` goldens reuse queries that would otherwise answer, with `seed_session_spent=4.0` under budget 5.0 so the next request trips the gate without needing stale or disagree evidence.

`pytest`: **76 passed**.

CI: `.github/workflows/eval.yml` runs pytest + `scripts/run_eval.py` on push/PR to main.

## Limitations

- Lexical grounding is not entailment; title-hash dense stub is not a real encoder.
- In-memory session ledger is process-local (demo API, not multi-tenant Redis).
- Approx cost units are heuristic, not dollar billing.
- Synthetic corpus / frozen clock; crafted golden set (1.000 scores are a harness, not prod claim).

## Hiring takeaway

Production agents need a refusal contract: evidence age, ranker agreement, grounding,
**and session spend**. Review `policy.py`, `cost_budget.py`, `disagreement.py`, and
`data/golden/questions.jsonl`.

## License

MIT. Author: M.Varun (`116015799+Mavarun@users.noreply.github.com`).
