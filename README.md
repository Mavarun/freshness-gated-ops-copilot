# Freshness-gated ops copilot

Ops knowledge copilot that refuses when evidence fails a freshness SLA, grounding
check, retriever-agreement check, **session cost budget**, or **prompt-injection
canary** scan. Offline CI, frozen clock.

| Decision | Meaning |
| --- | --- |
| `ANSWER` | Fresh supporting evidence passed grounding |
| `REFUSE_STALE` | Supporting chunks older than the SLA |
| `REFUSE_UNGROUNDED` | Related retrieval does not support the ask |
| `REFUSE_NO_EVIDENCE` | Nothing in the corpus matches |
| `REFUSE_DISAGREE` | BM25 and title-hash dense stub disagree on top-k |
| `REFUSE_CANARY` | Extractive draft echoed a planted canary not justified by the query |
| `REFUSE_BUDGET` | Session spent + request `approx_cost_units` would exceed session budget |



## Hypothesis (2026-09-19 prompt-injection canary farm)

1. Plant unique `CNRY-*` canary tokens in a subset of corpus docs; if an extractive
   answer echoes a canary that is **not** present in the query, policy emits
   `REFUSE_CANARY` (exfiltration / prompt-injection signal).
2. Queries that should not need those docs must not surface canaries in answers
   (clean controls stay `ANSWER` with empty canary leak sets).
3. Golden cases labeled with `expect_canary_leak` show canary-detection
   **precision / recall / F1** on the frozen offline eval.

Policy order (after budget): no-evidence → ungrounded → stale → disagree → grounding →
**canary** → answer. Canary token values are withheld from refusal text.

### Canary metrics (frozen clock 2026-09-13)

| Metric | Value |
| --- | ---: |
| canary_precision | 1.000 |
| canary_recall | 1.000 |
| canary_f1 | 1.000 |
| n_canary_labeled | 6 |
| decision_accuracy (full golden) | 1.000 |

Weaknesses: exact-string canaries (not paraphrased exfiltration); extractive path must
pull the planted sentence; justified queries must literally name the token; lexical
bleed from canary docs can nudge nearby no-evidence boundaries.


## Hypothesis (2026-09-20 session cost budget)

1. Production agents need a hard session cost budget; exceeding it must `REFUSE_BUDGET` **before answering**.
2. Traces already carry `approx_cost_units` — accumulate per `session_id` and gate in policy.
3. Golden + API tests prove budget trips **independently** of freshness/disagreement.

Prior (2026-09-16): disagreement routing. Prior (2026-09-15): FastAPI. Prior (2026-09-14): per-source SLAs.

## Architecture (budget first, canary after grounding)

```
query (+ optional session_id)
  -> budget gate (REFUSE_BUDGET if spent + cost > budget)
  -> retrieve BM25 + TitleHashDenseStub
  -> support / freshness / disagreement / grounding
  -> canary scan on extractive draft (REFUSE_CANARY on unjustified echo)
  -> ANSWER | REFUSE_*
  -> record cost on session ledger
```

Defaults: `use_budget_gate=True`, `session_budget_cost_units=5.0`; `use_canary_gate=True`.

## Package

```
src/ops_copilot/
  canary.py          CanaryRegistry + scan_answer / canary_detection_metrics
  cost_budget.py     SessionCostLedger (spent/record/seed/would_exceed)
  policy.py          REFUSE_BUDGET first; REFUSE_CANARY after grounding
  pipeline.py        ask(..., session_id=); canary scan on draft
  eval.py            golden seeds + canary P/R/F1 + budget_refuse_rate
  api.py             optional session_id; response includes canary dict
data/canaries/       offline CNRY registry
data/corpus/canary_docs.jsonl
```

## How to run

```bash
python -m pip install -e ".[dev,api]"
pytest
python scripts/run_eval.py
python scripts/run_api.py
```

## Golden eval (real run — 2026-09-19 canary farm)

41 labeled cases on frozen clock `2026-09-13T00:00:00+00:00`.

| Metric | Per-source + disagreement + budget + canary |
| --- | ---: |
| cases | 41 |
| decision_accuracy | 1.000 |
| refusal_precision | 1.000 |
| refusal_recall | 1.000 |
| answer_grounding_rate | 1.000 |
| disagreement_rate | 0.268 |
| n_disagreed | 11 |
| budget_refuse_rate | 0.073 |
| n_budget_refused | 3 |
| canary_precision | 1.000 |
| canary_recall | 1.000 |
| canary_f1 | 1.000 |
| n_canary_labeled | 6 |

`pytest`: **84 passed** (76 prior + 8 canary).

CI: `.github/workflows/eval.yml` runs pytest + `scripts/run_eval.py` on push/PR to main.

## Limitations

- Lexical grounding is not entailment; title-hash dense stub is not a real encoder.
- Exact-string canaries miss paraphrased exfiltration; justified queries must name the token.
- In-memory session ledger is process-local (demo API, not multi-tenant Redis).
- Approx cost units are heuristic, not dollar billing.
- Synthetic corpus / frozen clock; crafted golden set (1.000 scores are a harness, not prod claim).

## Hiring takeaway

Production agents need a refusal contract: evidence age, ranker agreement, grounding,
session spend, **and injection canaries on retrieved evidence**. Review `policy.py`,
`canary.py`, `cost_budget.py`, and `data/golden/questions.jsonl`.

## License

MIT. Author: M.Varun (`116015799+Mavarun@users.noreply.github.com`).
