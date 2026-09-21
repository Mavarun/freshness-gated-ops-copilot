# Freshness-gated ops copilot

Ops knowledge copilot that refuses when evidence fails a freshness SLA, grounding
check, retriever-agreement check, **session cost budget**, or **prompt-injection
canary** scan — and holds mutating **writes** behind a **HITL approve** gate.
Offline CI, frozen clock.

| Decision | Meaning |
| --- | --- |
| `ANSWER` | Fresh supporting evidence passed grounding |
| `REFUSE_STALE` | Supporting chunks older than the SLA |
| `REFUSE_UNGROUNDED` | Related retrieval does not support the ask |
| `REFUSE_NO_EVIDENCE` | Nothing in the corpus matches |
| `REFUSE_DISAGREE` | BM25 and title-hash dense stub disagree on top-k |
| `REFUSE_CANARY` | Extractive draft echoed a planted canary not justified by the query |
| `REFUSE_BUDGET` | Session spent + request `approx_cost_units` would exceed session budget |
| `PROPOSE_WRITE` | Imperative write detected; pending HITL approve (never auto-executes) |



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



## Hypothesis (2026-09-21 HITL write gate)

1. Read-path `ANSWER` is fine; any proposed *write* (restart service, page oncall,
   patch config) must stay **PENDING** until explicit human approve.
2. Audit log records `propose → approve|reject` with **actor + timestamp**;
   **rejected writes never execute** (execute stub is hard-gated on `APPROVED`).
3. Golden + API tests prove writes cannot execute without approve.

Policy: after the session budget gate, write-intent heuristics emit `PROPOSE_WRITE`
instead of answering or mutating. How-to reads (`How do I restart…`) do **not** trip
the write gate. Existing freshness / disagreement / canary / budget gates stay intact
for the read path.

### HITL audit story

```
query with write intent
  -> budget gate (may REFUSE_BUDGET)
  -> detect_write_intent (restart|page_oncall|patch_config)
  -> HitlWriteLedger.propose  status=PENDING  audit+=propose(actor, ts)
  -> decision PROPOSE_WRITE  (no side effects)

POST /writes/{id}/approve {actor}
  -> audit+=approve → execute_stub → status=EXECUTED

POST /writes/{id}/reject {actor}
  -> audit+=reject → status=REJECTED  executed=false forever
```

### HITL metrics (frozen clock 2026-09-13)

| Metric | Value |
| --- | ---: |
| propose_write_rate | 0.087 |
| n_propose_write | 4 |
| decision_accuracy (full golden) | 1.000 |
| pytest | 96 passed |

Weaknesses: keyword/heuristic write detection (not an LLM planner); in-memory HITL
ledger is process-local; execute path is an offline stub (no real k8s/pager/config
side effects); polite paraphrases outside the regexes will miss.

## Hypothesis (2026-09-20 session cost budget)

1. Production agents need a hard session cost budget; exceeding it must `REFUSE_BUDGET` **before answering**.
2. Traces already carry `approx_cost_units` — accumulate per `session_id` and gate in policy.
3. Golden + API tests prove budget trips **independently** of freshness/disagreement.

Prior (2026-09-16): disagreement routing. Prior (2026-09-15): FastAPI. Prior (2026-09-14): per-source SLAs.

## Architecture (budget → HITL write → retrieve gates → canary)

```
query (+ optional session_id)
  -> budget gate (REFUSE_BUDGET if spent + cost > budget)
  -> write-intent heuristic → PROPOSE_WRITE (HitlWriteLedger PENDING)
  -> else retrieve BM25 + TitleHashDenseStub
  -> support / freshness / disagreement / grounding
  -> canary scan on extractive draft (REFUSE_CANARY on unjustified echo)
  -> ANSWER | REFUSE_*
  -> record cost on session ledger
```

Defaults: `use_budget_gate=True`, `session_budget_cost_units=5.0`; `use_canary_gate=True`; `use_hitl_write_gate=True`.

## Package

```
src/ops_copilot/
  write_actions.py   ProposedWrite schema + detect_write_intent heuristics
  hitl.py            HitlWriteLedger propose/approve/reject/execute_stub + audit
  canary.py          CanaryRegistry + scan_answer / canary_detection_metrics
  cost_budget.py     SessionCostLedger (spent/record/seed/would_exceed)
  policy.py          REFUSE_BUDGET → PROPOSE_WRITE → … → REFUSE_CANARY → ANSWER
  pipeline.py        ask(...); HITL propose on write intent
  eval.py            golden + canary P/R/F1 + budget_refuse_rate + propose_write_rate
  api.py             POST /query + /writes/{id}/approve|reject + /writes/pending
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

## Golden eval (real run — 2026-09-21 HITL write gate)

46 labeled cases on frozen clock `2026-09-13T00:00:00+00:00`.

| Metric | Per-source + disagreement + budget + canary + HITL |
| --- | ---: |
| cases | 46 |
| decision_accuracy | 1.000 |
| refusal_precision | 1.000 |
| refusal_recall | 1.000 |
| answer_grounding_rate | 1.000 |
| disagreement_rate | 0.304 |
| n_disagreed | 14 |
| budget_refuse_rate | 0.065 |
| n_budget_refused | 3 |
| canary_precision | 1.000 |
| canary_recall | 1.000 |
| canary_f1 | 1.000 |
| n_canary_labeled | 6 |
| propose_write_rate | 0.087 |
| n_propose_write | 4 |

`pytest`: **96 passed** (84 prior + 12 HITL write-gate).

CI: `.github/workflows/eval.yml` runs pytest + `scripts/run_eval.py` on push/PR to main.

## Limitations

- Lexical grounding is not entailment; title-hash dense stub is not a real encoder.
- Exact-string canaries miss paraphrased exfiltration; justified queries must name the token.
- In-memory session ledger is process-local (demo API, not multi-tenant Redis).
- In-memory HITL write ledger is process-local; execute path is an offline stub.
- Write-intent detection is keyword/heuristic (misses paraphrases outside regexes).
- Approx cost units are heuristic, not dollar billing.
- Synthetic corpus / frozen clock; crafted golden set (1.000 scores are a harness, not prod claim).

## Hiring takeaway

Production agents need a refusal contract: evidence age, ranker agreement, grounding,
session spend, injection canaries, **and HITL for mutating writes**. Review
`policy.py`, `hitl.py`, `write_actions.py`, `canary.py`, `cost_budget.py`, and
`data/golden/questions.jsonl`.

## License

MIT. Author: M.Varun (`116015799+Mavarun@users.noreply.github.com`).
