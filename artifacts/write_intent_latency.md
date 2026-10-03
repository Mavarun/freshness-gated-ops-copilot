# Write-intent latency

Machine-dependent; 48 eval queries x 20 reps, single thread, frozen embedding fixture (no model load). Microseconds.

| component | p50 us | p95 us |
|---|---|---|
| PR #12 keyword regex | 18 | 29 |
| classifier: lexicon parser only (no mood) | 52 | 79 |
| classifier: + mood detection (default) | 42 | 67 |
| classifier: + mood, embedding on | 41 | 65 |
| classifier: + mood + prototype backoff (embedding on) | 44 | 102 |
| full pipeline ask: lexicon parser only (no mood) | 4046 | 7073 |
| full pipeline ask: + mood detection (default) | 3997 | 7042 |
| full pipeline ask: + mood, embedding on | 3995 | 7074 |
| full pipeline ask: + mood + prototype backoff (embedding on) | 4068 | 7104 |

Full pipeline over the 203 perturbed robustness rows (ms per query, `RobustnessReport.latency_summary`):

| config | p50 ms | p95 ms | mean ms |
|---|---|---|---|
| lexicon parser only (no mood) | 4.19 | 6.87 | 4.51 |
| + mood detection (default) | 4.32 | 6.92 | 4.60 |
| + mood, embedding on | 3.84 | 7.01 | 4.23 |
| + mood + prototype backoff (embedding on) | 3.69 | 6.43 | 4.07 |
