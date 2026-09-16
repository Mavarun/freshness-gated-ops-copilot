# Freshness-gated ops copilot — BM25-only vs dual disagreement

Frozen clock: `2026-09-13T00:00:00+00:00`. Same corpus, same golden set.
Dual path compares BM25 top-k doc_ids vs `TitleHashDenseStub` (char n-gram
hashing cosine over titles) and refuses with `REFUSE_DISAGREE` when Jaccard
falls below the configured threshold.

## Metrics comparison

| Metric | BM25-only (gate off) | Dual disagreement |
| --- | ---: | ---: |
| cases | 32 | 32 |
| decision_accuracy | 1.000 | 1.000 |
| refusal_precision | 1.000 | 1.000 |
| refusal_recall | 1.000 | 1.000 |
| answer_grounding_rate | 1.000 | 1.000 |
| disagreement_rate | 0.344 | 0.344 |
| n_disagreed | 11 | 11 |
| p50_latency_ms | 2.28 | 2.19 |
| p95_latency_ms | 3.61 | 2.73 |

## Decision flips vs BM25-only (n=4)

| Query | BM25-only | Dual | Jaccard | Note |
| --- | --- | --- | ---: | --- |
| What is the sidecar mesh mtls handshake budget? | `ANSWER` | `REFUSE_DISAGREE` | 0.000 | disagree-trap: BM25→cfg_mesh_mtls, ti... |
| What is the checkout canary stickiness salt? | `ANSWER` | `REFUSE_DISAGREE` | 0.000 | disagree-trap: BM25→cfg_stickiness, t... |
| What is the payments WAL checkpoint cadence? | `ANSWER` | `REFUSE_DISAGREE` | 0.000 | disagree-trap: BM25→cfg_wal, title-ha... |
| What is the checkout trace sample reservoir s... | `ANSWER` | `REFUSE_DISAGREE` | 0.000 | disagree-trap: BM25→cfg_reservoir, ti... |
