# Passage-rescue word-meaning check (post-hoc probe, selects nothing)

Rows: 171 dev5 calibration rows (no dev5 confirm, no held-out), 51 clean golden, tests/ sweep.

| config | calib correct | calib ANSWER | fail-open | must-refuse opened | clean |
| :--- | ---: | ---: | ---: | :--- | ---: |
| shipped default | 92/171 | 26/88 | 1 | d5-38 | 1.000 |
| + passage sense check | 57/171 | 9/88 | 0 | - | 1.000 |

Fixed: d5-38. New errors: 36 (dev 2, dev2 10, dev3 15, dev4 5, dev5_tune 4).
Sweep: 10 changed decisions, 0 opened, 0 labelled traps opened.
Decision: ships off: closes d5-38 but loses correct rows (no-new-error rule fails).
