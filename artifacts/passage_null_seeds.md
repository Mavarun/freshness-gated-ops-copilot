# Seed sensitivity of the shipped null-control test (pre-registered, `passage_null_seeds.py`)

Shipped default with only the control-word seed (and, secondary, the control count) changed. Rows: 171 calibration rows, 36 attribute traps, 51 clean golden; no unseen set is used.

## Primary: 100 controls (shipped)

Seed 42: calibration 88/171 (ANSWER 24), traps opened 0/36, must-refuse opened none, clean 1.000.
Seeds 1-20: calibration 85-89; 1 of 20 seeds safe; unsafe seeds: [2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20]; seeds drifting > 3 rows: none. **Seed-stable: no.**

| seed | clean | calib correct | calib ANSWER | traps opened | must-refuse opened |
| ---: | ---: | ---: | ---: | :--- | :--- |
| 1 | 1.000 | 86 | 23 | - | - |
| 2 | 1.000 | 87 | 24 | at-12, at-22 | - |
| 3 | 1.000 | 89 | 24 | at-12, at-22 | - |
| 4 | 1.000 | 88 | 24 | at-12, at-22, at-33 | - |
| 5 | 1.000 | 88 | 23 | at-22 | - |
| 6 | 1.000 | 88 | 24 | at-22 | - |
| 7 | 1.000 | 88 | 24 | at-12, at-22 | - |
| 8 | 1.000 | 89 | 24 | at-01, at-12, at-21, at-22, at-33 | - |
| 9 | 1.000 | 89 | 24 | at-12, at-22 | - |
| 10 | 1.000 | 88 | 24 | at-22 | - |
| 11 | 1.000 | 89 | 24 | at-22 | - |
| 12 | 1.000 | 88 | 23 | at-22 | - |
| 13 | 1.000 | 89 | 24 | at-12 | - |
| 14 | 1.000 | 88 | 24 | at-12, at-22 | - |
| 15 | 1.000 | 86 | 23 | at-22 | - |
| 16 | 1.000 | 88 | 24 | at-12, at-22 | - |
| 17 | 1.000 | 87 | 23 | at-12 | - |
| 18 | 1.000 | 88 | 24 | at-22 | - |
| 19 | 1.000 | 85 | 22 | at-22 | - |
| 20 | 1.000 | 87 | 24 | at-22 | - |

Calibration rows whose decision differs from seed 42 (number of seeds): d2-17 (3), d3-02 (4), d3-28 (5), d4-29 (7).

## Secondary (recorded only): 300 controls

Seed 42: calibration 88/171 (ANSWER 24), traps opened 0/36, must-refuse opened none, clean 1.000.
Seeds 1-20: calibration 87-89; 1 of 20 seeds safe; unsafe seeds: [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 14, 15, 16, 17, 18, 19, 20]; seeds drifting > 3 rows: none. **Seed-stable: no.**

| seed | clean | calib correct | calib ANSWER | traps opened | must-refuse opened |
| ---: | ---: | ---: | ---: | :--- | :--- |
| 1 | 1.000 | 87 | 24 | at-22 | - |
| 2 | 1.000 | 87 | 24 | at-12, at-22 | - |
| 3 | 1.000 | 89 | 24 | at-22 | - |
| 4 | 1.000 | 89 | 24 | at-12, at-22 | - |
| 5 | 1.000 | 89 | 24 | at-12, at-22 | - |
| 6 | 1.000 | 88 | 24 | at-12, at-22 | - |
| 7 | 1.000 | 87 | 23 | at-12, at-22 | - |
| 8 | 1.000 | 88 | 24 | at-12, at-22, at-33 | - |
| 9 | 1.000 | 89 | 24 | at-12, at-22 | - |
| 10 | 1.000 | 88 | 24 | at-22 | - |
| 11 | 1.000 | 88 | 24 | at-22 | - |
| 12 | 1.000 | 88 | 24 | at-22 | - |
| 13 | 1.000 | 88 | 24 | - | - |
| 14 | 1.000 | 87 | 23 | at-22 | - |
| 15 | 1.000 | 88 | 24 | at-22 | - |
| 16 | 1.000 | 87 | 24 | at-22 | - |
| 17 | 1.000 | 88 | 24 | at-22 | - |
| 18 | 1.000 | 88 | 24 | at-22 | - |
| 19 | 1.000 | 88 | 24 | at-22 | - |
| 20 | 1.000 | 88 | 24 | at-22 | - |

Calibration rows whose decision differs from seed 42 (number of seeds): d2-17 (1), d3-02 (1), d3-28 (3), d4-29 (4).
