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
