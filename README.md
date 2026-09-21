# Freshness-gated ops copilot

Ops knowledge copilot that refuses when evidence fails a freshness SLA, grounding
check, retriever-agreement check, **session cost budget**, **prompt-injection
canary** scan, or **PII/secret redaction** gate — and holds mutating **writes**
behind a **HITL approve** gate. Offline CI, frozen clock.

| Decision | Meaning |
| --- | --- |
| `ANSWER` | Fresh supporting evidence passed grounding |
| `REFUSE_STALE` | Supporting chunks older than the SLA |
| `REFUSE_UNGROUNDED` | Related retrieval does not support the ask |
| `REFUSE_NO_EVIDENCE` | Nothing in the corpus matches |
| `REFUSE_DISAGREE` | BM25 and title-hash dense stub disagree on top-k |
| `REFUSE_CANARY` | Extractive draft echoed a planted canary not justified by the query |
| `REFUSE_PII` | Draft contained unauthorized PII/secrets (or secrets that never authorize) |
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
| pytest | 110 passed |

Weaknesses: keyword/heuristic write detection (not an LLM planner); in-memory HITL
ledger is process-local; execute path is an offline stub (no real k8s/pager/config
side effects); polite paraphrases outside the regexes will miss.


## Hypothesis (2026-09-22 PII / secret redaction gate)

1. Extractive answers can leak emails, API keys, and phone numbers planted in ops
   docs; a post-answer scanner must **redact** or emit `REFUSE_PII`.
2. Queries that *explicitly* ask for a rotation contact email (keyword allowlist)
   may receive a **masked** contact form — never the raw address. AWS-like keys and
   Slack tokens **never** authorize.
3. Golden cases labeled with `expect_pii` prove PII-detection **precision / recall / F1**
   independently of freshness/canary.

**Policy (clear):** unauthorized email/phone in the draft → `REFUSE_PII`. Allowlisted
contact queries → `ANSWER` with masked values (`o***@example.com`, `***-***-2890`).
Any `aws_key` / `slack_token` match → always `REFUSE_PII`. Existing freshness /
disagreement / canary / budget / HITL gates stay intact; PII runs after canary.

### PII metrics (frozen clock 2026-09-13)

| Metric | Value |
| --- | ---: |
| pii_precision | 1.000 |
| pii_recall | 1.000 |
| pii_f1 | 1.000 |
| n_pii_labeled | 5 |
| decision_accuracy (full golden) | 1.000 |
| pytest | 110 passed |

Weaknesses: regex detectors (no NER); phone patterns are US/E.164-biased; authorize
allowlist is keyword-exact; corpus bleed can nudge nearby no-evidence/ungrounded
boundaries; secrets refusal does not attempt partial mask-and-answer.

## Hypothesis (2026-09-20 session cost budget)

1. Production agents need a hard session cost budget; exceeding it must `REFUSE_BUDGET` **before answering**.
2. Traces already carry `approx_cost_units` — accumulate per `session_id` and gate in policy.
3. Golden + API tests prove budget trips **independently** of freshness/disagreement.

Prior (2026-09-16): disagreement routing. Prior (2026-09-15): FastAPI. Prior (2026-09-14): per-source SLAs.

## Architecture (budget → HITL write → retrieve gates → canary → PII)

```
query (+ optional session_id)
  -> budget gate (REFUSE_BUDGET if spent + cost > budget)
  -> write-intent heuristic → PROPOSE_WRITE (HitlWriteLedger PENDING)
  -> else retrieve BM25 + TitleHashDenseStub
  -> support / freshness / disagreement / grounding
  -> canary scan on extractive draft (REFUSE_CANARY on unjustified echo)
  -> PII scan (REFUSE_PII or mask authorized contacts)
  -> ANSWER | REFUSE_*
  -> record cost on session ledger
```

Defaults: `use_budget_gate=True`, `session_budget_cost_units=5.0`; `use_canary_gate=True`; `use_hitl_write_gate=True`; `use_pii_gate=True`.

## Package

```
src/ops_copilot/
  write_actions.py   ProposedWrite schema + detect_write_intent heuristics
  hitl.py            HitlWriteLedger propose/approve/reject/execute_stub + audit
  canary.py          CanaryRegistry + scan_answer / canary_detection_metrics
  pii.py             PII/secret detector patterns (email/phone/AWS/Slack)
  pii_redact.py      mask helpers + scan_answer_pii authorize/refuse policy
  cost_budget.py     SessionCostLedger (spent/record/seed/would_exceed)
  policy.py          … → REFUSE_CANARY → REFUSE_PII → ANSWER
  pipeline.py        ask(...); HITL propose; PII scan/redact on draft
  eval.py            golden + canary/pii P/R/F1 + budget + propose_write rates
  api.py             POST /query (+ pii_detected, redactions_count) + HITL writes
data/canaries/       offline CNRY registry
data/corpus/canary_docs.jsonl
data/corpus/pii_docs.jsonl
```

## How to run

```bash
python -m pip install -e ".[dev,api]"
pytest
python scripts/run_eval.py
python scripts/run_api.py
```

## Golden eval (real run — 2026-09-22 PII redaction gate)

51 labeled cases on frozen clock `2026-09-13T00:00:00+00:00`.

| Metric | Per-source + disagreement + budget + canary + HITL + PII |
| --- | ---: |
| cases | 51 |
| decision_accuracy | 1.000 |
| refusal_precision | 1.000 |
| refusal_recall | 1.000 |
| answer_grounding_rate | 1.000 |
| disagreement_rate | 0.275 |
| n_disagreed | 14 |
| budget_refuse_rate | 0.059 |
| n_budget_refused | 3 |
| canary_precision | 1.000 |
| canary_recall | 1.000 |
| canary_f1 | 1.000 |
| n_canary_labeled | 6 |
| propose_write_rate | 0.078 |
| n_propose_write | 4 |
| pii_precision | 1.000 |
| pii_recall | 1.000 |
| pii_f1 | 1.000 |
| n_pii_labeled | 5 |

`pytest`: **110 passed** (96 prior + 14 PII redaction-gate).

CI: `.github/workflows/eval.yml` runs pytest + `scripts/run_eval.py` on push/PR to main.

## Limitations

- Lexical grounding is not entailment; title-hash dense stub is not a real encoder.
- Exact-string canaries miss paraphrased exfiltration; justified queries must name the token.
- In-memory session ledger is process-local (demo API, not multi-tenant Redis).
- In-memory HITL write ledger is process-local; execute path is an offline stub.
- Write-intent detection is keyword/heuristic (misses paraphrases outside regexes).
- Approx cost units are heuristic, not dollar billing.
- Regex PII detectors (no NER); authorize allowlist is keyword-exact; US/E.164 phone bias.
- Secrets always refuse (no mask-and-answer path for AWS/Slack tokens).
- Synthetic corpus / frozen clock; crafted golden set (1.000 scores are a harness, not prod claim).

## Hiring takeaway

Production agents need a refusal contract: evidence age, ranker agreement, grounding,
session spend, injection canaries, PII/secret redaction, **and HITL for mutating writes**. Review
`policy.py`, `hitl.py`, `write_actions.py`, `canary.py`, `pii.py`, `cost_budget.py`, and
`data/golden/questions.jsonl`.

## License

MIT. Author: M.Varun (`116015799+Mavarun@users.noreply.github.com`).
