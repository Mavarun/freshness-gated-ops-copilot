# The shipped null test without a seed (report-only, `passage_null_exact.py`)

Pool: 5067 control words. 70 of 207 rows reach the null test (at most 5 calls per row). Trees reproduce all 21 seeds of the 2026-10-26 sweep exactly (tested).

Seed 42 (shipped): calibration 88/171, traps opened 0/36.

## Over 10,000 uniform control samples (shared by every row, as one seed is)

| controls | P(no trap opens) | P(safe) | mean traps opened | calibration correct, mean [5%, 95%] |
| ---: | ---: | ---: | ---: | :--- |
| 100 | 0.047 | 0.047 | 1.61 | 87.9 [86, 89] |
| 300 | 0.004 | 0.004 | 1.57 | 88.2 [87, 89] |

Traps opened per sample (100 controls): 0: 472, 1: 4040, 2: 4887, 3: 360, 4: 2, 5: 239.

| trap | P(open), 100 controls | P(open), 300 controls | pool percentile of each call |
| :--- | ---: | ---: | :--- |
| at-01 | 0.024 | 0.000 | 0.213, 0.213 |
| at-12 | 0.574 | 0.573 | 0.303, 0.303 |
| at-21 | 0.024 | 0.000 | 0.213, 0.213 |
| at-22 | 0.926 | 0.993 | 0.826, 0.363, 0.363 |
| at-33 | 0.061 | 0.002 | 0.230, 0.230 |

## Whole-pool percentile (seed-free mode) on the same seen rows

| q | calibration correct | ANSWER correct | traps opened | must-refuse opened |
| ---: | ---: | ---: | :--- | :--- |
| 0.20 | 90 | 25 | at-01, at-12, at-21, at-22, at-33 | - |
| 0.22 | 89 | 24 | at-12, at-22, at-33 | - |
| 0.24 | 89 | 24 | at-12, at-22 | - |
| 0.26 | 89 | 24 | at-12, at-22 | - |
| 0.28 | 89 | 24 | at-12, at-22 | - |
| 0.30 | 88 | 24 | at-12, at-22 | - |
| 0.32 | 88 | 24 | at-22 | - |
| 0.34 | 88 | 24 | at-22 | - |
| 0.36 | 85 | 22 | at-22 | - |
| 0.38 | 85 | 22 | - | - |
| 0.40 | 83 | 22 | - | - |
| 0.42 | 81 | 20 | - | - |
| 0.44 | 81 | 20 | - | - |
| 0.46 | 81 | 20 | - | - |
| 0.48 | 81 | 20 | - | - |
| 0.50 | 80 | 19 | - | - |
