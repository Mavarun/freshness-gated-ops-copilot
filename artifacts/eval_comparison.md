# Freshness-gated ops copilot — global vs per-source SLA

Frozen clock: `2026-09-13T00:00:00+00:00`. Same corpus, same golden set.

## Metrics comparison

| Metric | Global-only (48h) | Per-source SLAs |
| --- | ---: | ---: |
| cases | 28 | 28 |
| decision_accuracy | 1.000 | 1.000 |
| refusal_precision | 1.000 | 1.000 |
| refusal_recall | 1.000 | 1.000 |
| answer_grounding_rate | 1.000 | 1.000 |
| p50_latency_ms | 1.43 | 1.49 |
| p95_latency_ms | 2.06 | 1.68 |

## Decision flips (n=4)

Queries where the two modes emit different decisions — the empirical
evidence that per-source SLAs change refusal behaviour on a fixed corpus.

| Query | Global-only | Per-source | Note |
| --- | --- | --- | --- |
| What is the production maintenance change window? | `REFUSE_STALE` | `ANSWER` | mixed-sla: confluence age~62h passes 7d SLA, ... |
| When does the production freeze start? | `REFUSE_STALE` | `ANSWER` | mixed-sla: same confluence policy page; globa... |
| What is the live payments-api request rate? | `ANSWER` | `REFUSE_STALE` | mixed-sla: grafana age~2.5h fails 1h SLA, pas... |
| What qps does the payments-api live scrape show? | `ANSWER` | `REFUSE_STALE` | mixed-sla: grafana under-protect if global-only |

## Per-source confusion

| Pair | Count |
| --- | ---: |
| `ANSWER->ANSWER` | 10 |
| `REFUSE_NO_EVIDENCE->REFUSE_NO_EVIDENCE` | 5 |
| `REFUSE_STALE->REFUSE_STALE` | 8 |
| `REFUSE_UNGROUNDED->REFUSE_UNGROUNDED` | 5 |

## Global-only confusion

| Pair | Count |
| --- | ---: |
| `ANSWER->ANSWER` | 10 |
| `REFUSE_NO_EVIDENCE->REFUSE_NO_EVIDENCE` | 5 |
| `REFUSE_STALE->REFUSE_STALE` | 8 |
| `REFUSE_UNGROUNDED->REFUSE_UNGROUNDED` | 5 |
