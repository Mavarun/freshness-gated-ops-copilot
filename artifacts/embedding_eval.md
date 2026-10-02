# Embedding path: latency, dense agreement, live vs frozen

Machine: Linux x86_64 python 3.13.5. Latency is per perturbed row (n=203), after one warm-up pass, wall clock inside `Copilot.ask`.

| config | p50 ms | p95 ms | mean ms | perturbed acc | held-out acc | fail-open |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| default (embedding off) | 3.69 | 5.14 | 3.82 | 0.862 | 0.400 | 0 |
| embedding retriever only [frozen] | 3.19 | 4.75 | 3.35 | 0.862 | 0.400 | 0 |
| semantic grounding only [frozen] | 3.92 | 5.82 | 4.12 | 0.887 | 0.486 | 0 |
| both (embedding on) [frozen] | 3.37 | 5.12 | 3.56 | 0.887 | 0.486 | 0 |
| both, strict off (unsafe) [frozen] | 3.26 | 4.90 | 3.40 | 0.887 | 0.543 | 1 |
| both (embedding on) [live model] | 8.51 | 11.34 | 8.59 | 0.887 | 0.486 | 0 |

Dense top-1 agreement on 254 rewritten eval queries: BM25 vs title-hash stub 182, BM25 vs MiniLM 186, stub vs MiniLM 191.

Live model vs frozen fixture: worst query cosine 1.000000; decision mismatches 0 of 254.
