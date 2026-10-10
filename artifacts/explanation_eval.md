# Refusal-explanation eval

Expectations: `data/eval/explanation_expectations.jsonl`, one hand-written row per refusing golden case (33), taken from each golden row's note. Stale ages and SLAs are recomputed from `data/corpus/*.jsonl` and `config/source_slas.yaml` independently of the pipeline. Transfer = perturbed rows refused with the same decision as their golden source, checked against that source's expectation. Leaks = canary tokens, PII, secret patterns or the literal planted values found in any explanation or refusal reason (golden, 203 perturbed, write refusals, and probe queries that paste each planted value and synthetic secrets).

| config | golden rows fully correct | golden checks | schema ok (golden / perturbed) | transfer rows | transfer checks | write reason codes | did-you-mean | leaks |
|---|---|---|---|---|---|---|---|---|
| default | 33/33 (1.000) | 182/182 (1.000) | 51/51 / 203/203 | 111/120 (0.925) | 406/415 (0.978) | 10/11 | 5/5 | 0 |
| embedding on (frozen MiniLM) | 33/33 (1.000) | 182/182 (1.000) | 51/51 / 203/203 | 114/123 (0.927) | 418/427 (0.979) | 10/11 | 5/5 | 0 |

## default: checks

| check | golden | perturbed transfer |
|---|---|---|
| bm25_doc_correct | 4/4 (1.000) | 13/13 (1.000) |
| budget_correct | 3/3 (1.000) | 12/12 (1.000) |
| canary_doc_correct | 4/4 (1.000) | 13/13 (1.000) |
| decision_correct | 33/33 (1.000) | - |
| dense_doc_correct | 4/4 (1.000) | 13/13 (1.000) |
| gate_correct | 33/33 (1.000) | - |
| missing_term_named | 11/11 (1.000) | 37/44 (0.841) |
| pii_doc_correct | 3/3 (1.000) | 10/10 (1.000) |
| pii_kind_correct | 3/3 (1.000) | 10/10 (1.000) |
| projected_exceeds_budget | 3/3 (1.000) | 12/12 (1.000) |
| remediation_add_runbook | 11/11 (1.000) | 44/44 (1.000) |
| remediation_new_session | 3/3 (1.000) | 12/12 (1.000) |
| remediation_quarantine | 4/4 (1.000) | 13/13 (1.000) |
| remediation_reconcile | 4/4 (1.000) | 13/13 (1.000) |
| remediation_refresh_source | 8/8 (1.000) | 28/28 (1.000) |
| remediation_scrub | 3/3 (1.000) | 10/10 (1.000) |
| stale_age_correct | 8/8 (1.000) | 28/28 (1.000) |
| stale_doc_first | 8/8 (1.000) | 26/28 (0.929) |
| stale_doc_named | 8/8 (1.000) | 28/28 (1.000) |
| stale_over_by_correct | 8/8 (1.000) | 28/28 (1.000) |
| stale_sla_correct | 8/8 (1.000) | 28/28 (1.000) |
| stale_source_system_correct | 8/8 (1.000) | 28/28 (1.000) |

Leak scan: 8 planted values (canary tokens + corpus PII/secrets), 84 probe queries (83 refused); leaks by section {'golden': 0, 'perturbed': 0, 'write': 0, 'probes': 0}.

Trace-bound fields (`query`, `reason`, `write_intent`, `proposed_write`, `explanation`): **89 rows / 236 leaks unredacted (as PR #14 wrote them) -> 0 rows / 0 leaks redacted (as written now)**.

| section | rows | rows leaking raw | rows leaking redacted | raw leaks | redacted leaks |
|---|---:|---:|---:|---:|---:|
| golden | 51 | 1 | 0 | 2 | 0 |
| perturbed | 203 | 4 | 0 | 8 | 0 |
| write | 11 | 0 | 0 | 0 | 0 |
| probes | 84 | 84 | 0 | 226 | 0 |

Secrets disclosed in words (35 probes = 0 templates still leaking now; synthetic shapeless secrets after a credential noun, templates written together with the pattern, so not blind): distinctive secret words left in trace-bound fields.

| redaction | rows leaking | secret words leaked |
|---|---:|---:|
| none (raw) | 35 | 70 / 70 |
| PR #15 patterns | 33 | 65 / 70 |
| now (+ disclosed-secret pattern) | 0 | 0 / 70 |

Over-redaction cost: trace `query` changed by the new pattern on 0 golden, 0 perturbed and 0 write-refusal rows.

Random tokens with no format and no credential cue (105 probes: seeded synthetic secrets of every `secret_entropy` family x 5 templates; written with the detector, so not blind): rows whose trace-bound fields still hold the secret string. The PR #16 column re-redacts the boundary fields only (explanations are redacted when built).

| family | rows | none (raw) | PR #16 patterns | now (+ random-token detector) |
|---|---:|---:|---:|---:|
| base62 | 15 | 15 | 15 | 0 |
| hex | 15 | 15 | 15 | 0 |
| lower_alnum | 15 | 15 | 15 | 0 |
| base64url | 15 | 15 | 15 | 0 |
| password_symbols | 15 | 15 | 15 | 0 |
| prefixed_pat | 15 | 15 | 15 | 0 |
| pronounceable (not gating) | 15 | 15 | 15 | 5 |
| **all** | 105 | 105 | 105 | 5 |

Over-redaction cost: trace `query` changed by the detector on 0 golden, 0 perturbed and 0 write-refusal rows.

## embedding on (frozen MiniLM): checks

| check | golden | perturbed transfer |
|---|---|---|
| bm25_doc_correct | 4/4 (1.000) | 14/14 (1.000) |
| budget_correct | 3/3 (1.000) | 12/12 (1.000) |
| canary_doc_correct | 4/4 (1.000) | 14/14 (1.000) |
| decision_correct | 33/33 (1.000) | - |
| dense_doc_correct | 4/4 (1.000) | 14/14 (1.000) |
| gate_correct | 33/33 (1.000) | - |
| missing_term_named | 11/11 (1.000) | 37/44 (0.841) |
| pii_doc_correct | 3/3 (1.000) | 10/10 (1.000) |
| pii_kind_correct | 3/3 (1.000) | 10/10 (1.000) |
| projected_exceeds_budget | 3/3 (1.000) | 12/12 (1.000) |
| remediation_add_runbook | 11/11 (1.000) | 44/44 (1.000) |
| remediation_new_session | 3/3 (1.000) | 12/12 (1.000) |
| remediation_quarantine | 4/4 (1.000) | 14/14 (1.000) |
| remediation_reconcile | 4/4 (1.000) | 14/14 (1.000) |
| remediation_refresh_source | 8/8 (1.000) | 29/29 (1.000) |
| remediation_scrub | 3/3 (1.000) | 10/10 (1.000) |
| stale_age_correct | 8/8 (1.000) | 29/29 (1.000) |
| stale_doc_first | 8/8 (1.000) | 27/29 (0.931) |
| stale_doc_named | 8/8 (1.000) | 29/29 (1.000) |
| stale_over_by_correct | 8/8 (1.000) | 29/29 (1.000) |
| stale_sla_correct | 8/8 (1.000) | 29/29 (1.000) |
| stale_source_system_correct | 8/8 (1.000) | 29/29 (1.000) |

Leak scan: 8 planted values (canary tokens + corpus PII/secrets), 84 probe queries (83 refused); leaks by section {'golden': 0, 'perturbed': 0, 'write': 0, 'probes': 0}.

Trace-bound fields (`query`, `reason`, `write_intent`, `proposed_write`, `explanation`): **89 rows / 236 leaks unredacted (as PR #14 wrote them) -> 0 rows / 0 leaks redacted (as written now)**.

| section | rows | rows leaking raw | rows leaking redacted | raw leaks | redacted leaks |
|---|---:|---:|---:|---:|---:|
| golden | 51 | 1 | 0 | 2 | 0 |
| perturbed | 203 | 4 | 0 | 8 | 0 |
| write | 11 | 0 | 0 | 0 | 0 |
| probes | 84 | 84 | 0 | 226 | 0 |

Secrets disclosed in words (35 probes = 0 templates still leaking now; synthetic shapeless secrets after a credential noun, templates written together with the pattern, so not blind): distinctive secret words left in trace-bound fields.

| redaction | rows leaking | secret words leaked |
|---|---:|---:|
| none (raw) | 35 | 70 / 70 |
| PR #15 patterns | 33 | 65 / 70 |
| now (+ disclosed-secret pattern) | 0 | 0 / 70 |

Over-redaction cost: trace `query` changed by the new pattern on 0 golden, 0 perturbed and 0 write-refusal rows.

Random tokens with no format and no credential cue (105 probes: seeded synthetic secrets of every `secret_entropy` family x 5 templates; written with the detector, so not blind): rows whose trace-bound fields still hold the secret string. The PR #16 column re-redacts the boundary fields only (explanations are redacted when built).

| family | rows | none (raw) | PR #16 patterns | now (+ random-token detector) |
|---|---:|---:|---:|---:|
| base62 | 15 | 15 | 15 | 0 |
| hex | 15 | 15 | 15 | 0 |
| lower_alnum | 15 | 15 | 15 | 0 |
| base64url | 15 | 15 | 15 | 0 |
| password_symbols | 15 | 15 | 15 | 0 |
| prefixed_pat | 15 | 15 | 15 | 0 |
| pronounceable (not gating) | 15 | 15 | 15 | 5 |
| **all** | 105 | 105 | 105 | 5 |

Over-redaction cost: trace `query` changed by the detector on 0 golden, 0 perturbed and 0 write-refusal rows.
