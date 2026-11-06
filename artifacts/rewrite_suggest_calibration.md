# Verified rewrites, calibration (dev2-dev6)

Null control (`context` row only): random corpus words swapped for the missing term.

| arm | rescuable | traps | coverage | doc_hit_1 | anchor_hit_1 | anchor_hit_3 | anchor_precision_1 | trap_invitation | null_verify_rate |
| :--- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `idf` | 93 | 42 | 0.957 | 0.957 | 0.247 | 0.344 | 0.258 | 0.500 | 0.000 |
| `first` | 93 | 42 | 0.957 | 0.957 | 0.151 | 0.290 | 0.157 | 0.548 | 0.000 |
| `context` | 93 | 42 | 0.957 | 0.957 | 0.430 | 0.538 | 0.449 | 0.548 | 0.436 |
| `context_mc1` | 93 | 42 | 0.914 | 0.914 | 0.430 | 0.441 | 0.471 | 0.548 | 0.000 |
| `context_mc2` | 93 | 42 | 0.634 | 0.634 | 0.430 | 0.441 | 0.678 | 0.286 | 0.000 |
| `context_pairs` | 93 | 42 | 0.957 | 0.957 | 0.430 | 0.538 | 0.449 | 0.786 | 0.000 |
| `context_mc1_pairs` | 93 | 42 | 0.914 | 0.914 | 0.430 | 0.441 | 0.471 | 0.786 | 0.000 |

Picked: `context_mc2`.
