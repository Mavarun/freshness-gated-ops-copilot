# Freshness-gated ops copilot — BM25-only vs dual disagreement

Frozen clock: `2026-09-13T00:00:00+00:00`. Same corpus, same golden set.

## Metrics comparison

| Metric | BM25-only (gate off) | Dual (disagreement gate) |
| --- | ---: | ---: |
| cases | 35 | 35 |
| decision_accuracy | 1.000 | 1.000 |
| disagreement_rate | 0.314 | 0.114 |
| budget_refuse_rate | 0.086 | 0.086 |
| n_budget_refused | 3 | 3 |

## Decision flips (n=4)

| Query | BM25-only | Dual | Note |
| --- | --- | --- | --- |
| What is the sidecar mesh mtls handshake budget? | `ANSWER` | `REFUSE_DISAGREE` | disagree-trap |
| What is the checkout canary stickiness salt? | `ANSWER` | `REFUSE_DISAGREE` | disagree-trap |
| What is the payments WAL checkpoint cadence? | `ANSWER` | `REFUSE_DISAGREE` | disagree-trap |
| What is the checkout trace sample reservoir size? | `ANSWER` | `REFUSE_DISAGREE` | disagree-trap |
