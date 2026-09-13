# Freshness-gated ops copilot — golden eval

Frozen clock: `2026-09-13T00:00:00+00:00`. SLA: `max_age_hours=48`.

## Summary metrics

| Metric | Value |
| --- | ---: |
| cases | 24 |
| decision_accuracy | 1.000 |
| refusal_precision | 1.000 |
| refusal_recall | 1.000 |
| answer_grounding_rate | 1.000 |
| p50_latency_ms | 1.54 |
| p95_latency_ms | 1.87 |

## Confusion (expect → actual)

| Pair | Count |
| --- | ---: |
| `ANSWER->ANSWER` | 8 |
| `REFUSE_NO_EVIDENCE->REFUSE_NO_EVIDENCE` | 5 |
| `REFUSE_STALE->REFUSE_STALE` | 6 |
| `REFUSE_UNGROUNDED->REFUSE_UNGROUNDED` | 5 |

## Cases

| query | expect | actual | match | latency_ms | cited_ids | note |
| --- | --- | --- | --- | --- | --- | --- |
| What is the current checkout p99 latency? | ANSWER | ANSWER | True | 2.141 | pd_inc_4821,graf_checkout_sli,rb_checkout_latency | fresh-ok: Grafana + INC-4821 both state 2410ms |
| Is the checkout_retry feature flag enabled? | ANSWER | ANSWER | True | 1.505 | ff_checkout_retry | fresh-ok: LaunchDarkly 15 percent canary |
| Who is the primary on-call right now? | ANSWER | ANSWER | True | 1.456 | wiki_oncall_now | fresh-ok: Asha Patel; stale June rotation must not win |
| How many checkout-api replicas are running? | ANSWER | ANSWER | True | 1.588 | k8s_checkout_api,rb_checkout_latency | fresh-ok: k8s snapshot current replicas 12 |
| What is the remaining error budget for checkout? | ANSWER | ANSWER | True | 1.473 | dd_error_budget | fresh-ok: Datadog 31 percent remaining |
| What mitigation does the checkout latency runbook recommend? | ANSWER | ANSWER | True | 1.546 | rb_checkout_latency | fresh-ok: HPA 20, disable promo, raise pool 128 |
| What is the Redis checkout-pool utilization? | ANSWER | ANSWER | True | 1.597 | dd_redis_pool,rb_checkout_latency | fresh-ok: 49 of 50 connections, not the stale maxmemory doc |
| What is the status of the payments-api? | ANSWER | ANSWER | True | 1.609 | sp_payments_degraded | fresh-ok: statuspage degraded 12 percent 5xx |
| What is the Redis maxmemory-policy? | REFUSE_STALE | REFUSE_STALE | True | 1.381 |  | stale-must-refuse: only March 2026 runbook states the policy |
| How do we run the blue-green deploy procedure? | REFUSE_STALE | REFUSE_STALE | True | 1.485 |  | stale-must-refuse: Q1 procedure retired after mesh cutover |
| What is the auth token TTL? | REFUSE_STALE | REFUSE_STALE | True | 1.625 |  | stale-must-refuse: only Nov 2025 identity page |
| How do I drain Kafka consumer lag on payments-worker? | REFUSE_STALE | REFUSE_STALE | True | 1.651 |  | stale-must-refuse: April 2026 broker recipe |
| What was the Q1 checkout SLO target? | REFUSE_STALE | REFUSE_STALE | True | 1.437 |  | stale-must-refuse: Q1 archive dashboard 99.5 percent |
| How many replicas should payments-worker run? | REFUSE_STALE | REFUSE_STALE | True | 1.415 |  | stale-must-refuse: May k8s snapshot is the only replica count |
| How do I reset the SAP payroll connector? | REFUSE_NO_EVIDENCE | REFUSE_NO_EVIDENCE | True | 1.542 |  | no-evidence: SAP / payroll not in corpus |
| What is the Snowflake warehouse auto-suspend setting? | REFUSE_NO_EVIDENCE | REFUSE_NO_EVIDENCE | True | 1.533 |  | no-evidence: Snowflake absent |
| Who owns Android push-notification cert rotation? | REFUSE_NO_EVIDENCE | REFUSE_NO_EVIDENCE | True | 1.914 |  | no-evidence: mobile certs absent |
| What is the PCI DSS scan cadence for the vault cluster? | REFUSE_NO_EVIDENCE | REFUSE_NO_EVIDENCE | True | 1.478 |  | no-evidence: PCI / vault-cluster cadence absent |
| How do I provision a new Istio ingress gateway in eu-west-3? | REFUSE_NO_EVIDENCE | REFUSE_NO_EVIDENCE | True | 1.448 |  | no-evidence: Istio / eu-west-3 absent |
| What is the rollback procedure for the checkout_retry feature flag? | REFUSE_UNGROUNDED | REFUSE_UNGROUNDED | True | 1.499 |  | ungrounded trap: flag state is documented, rollback procedure is not |
| What millicore CPU request is configured on checkout-api? | REFUSE_UNGROUNDED | REFUSE_UNGROUNDED | True | 1.584 |  | ungrounded trap: HPA utilization is documented, millicore CPU request is not |
| What is the database password rotation interval? | REFUSE_UNGROUNDED | REFUSE_UNGROUNDED | True | 1.578 |  | ungrounded trap: hygiene page mentions passwords, not a rotation interval |
| What is the chargeback playbook for INC-4821? | REFUSE_UNGROUNDED | REFUSE_UNGROUNDED | True | 1.485 |  | ungrounded trap: incident is documented, chargeback playbook is not |
| What IP allowlist is configured on the inc-4821 Slack webhook? | REFUSE_UNGROUNDED | REFUSE_UNGROUNDED | True | 1.579 |  | ungrounded trap: channel exists, webhook IP allowlist does not |
