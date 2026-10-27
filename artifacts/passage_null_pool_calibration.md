# Seed-free null test: calibration grid (pre-registered, `passage_null_pool.py`)

Rows: 171 calibration, 51 clean, 56 traps (36 first set + 20 v2 tune). Baseline (shipped, seed 42): 88/171 (ANSWER 24/88), traps opened none.

Safe = clean 1.000, no must-refuse or trap opened, sweep safe, at most 6 rows / 3 ANSWER lost. Selection: smallest safe q whose lower grid neighbour is also safe.

| q | safe | calib correct | ANSWER | rows lost | new errors | traps opened | must-refuse opened |
| ---: | :---: | ---: | ---: | ---: | :--- | :--- | :--- |
| 0.30 | no | 88 | 24 | 0 | - | at-12, at-22 | - |
| 0.32 | no | 88 | 24 | 0 | - | at-22 | - |
| 0.34 | no | 88 | 24 | 0 | - | at-22 | - |
| 0.36 | no | 85 | 22 | 3 | d2-17, d3-02, d3-28 | at-22 | - |
| 0.38 | yes | 85 | 22 | 3 | d2-17, d3-02, d3-28 | - | - |
| 0.40 | yes | 83 | 22 | 5 | d2-17, d2-24, d3-02, d3-28, d4-27 | - | - |
| 0.42 | no | 81 | 20 | 7 | d2-17, d2-24, d3-02, d3-10, d3-23, d3-28, d4-27 | - | - |
| 0.44 | no | 81 | 20 | 7 | d2-17, d2-24, d3-02, d3-10, d3-23, d3-28, d4-27 | - | - |
| 0.46 | no | 81 | 20 | 7 | d2-17, d2-24, d3-02, d3-10, d3-23, d3-28, d4-27 | - | - |
| 0.48 | no | 81 | 20 | 7 | d2-17, d2-24, d3-02, d3-10, d3-23, d3-28, d4-27 | - | - |
| 0.50 | no | 80 | 19 | 8 | d2-09, d2-17, d2-24, d3-02, d3-10, d3-23, d3-28, d4-27 | - | - |

2 of 11 settings safe. **Chosen: q = 0.40** (83/171, 5 rows lost).
