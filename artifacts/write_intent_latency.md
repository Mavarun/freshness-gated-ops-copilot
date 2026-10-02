# Write-intent latency

Machine-dependent; 48 eval queries x 20 reps, single thread, frozen embedding fixture (no model load). Microseconds.

| component | p50 us | p95 us |
|---|---|---|
| PR #12 keyword regex | 18 | 28 |
| classifier: lexicon parser only (no mood) | 48 | 74 |
| classifier: + mood detection (default) | 37 | 55 |
| classifier: + mood, embedding on | 37 | 54 |
| classifier: + mood + prototype backoff (embedding on) | 37 | 84 |
| full pipeline ask: lexicon parser only (no mood) | 3668 | 6273 |
| full pipeline ask: + mood detection (default) | 3627 | 6186 |
| full pipeline ask: + mood, embedding on | 3774 | 6413 |
| full pipeline ask: + mood + prototype backoff (embedding on) | 3785 | 6365 |

Full pipeline over the 203 perturbed robustness rows (ms per query, `RobustnessReport.latency_summary`):

| config | p50 ms | p95 ms | mean ms |
|---|---|---|---|
| lexicon parser only (no mood) | 4.02 | 5.82 | 4.17 |
| + mood detection (default) | 3.88 | 5.31 | 4.03 |
| + mood, embedding on | 3.35 | 4.75 | 3.48 |
| + mood + prototype backoff (embedding on) | 3.44 | 4.92 | 3.57 |
