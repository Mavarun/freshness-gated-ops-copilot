# Null-control test on passage rescues: calibration (v2, sticky veto)

Rows: 171 dev5 calibration rows + 18 attribute-trap tune rows (no dev5 confirm, no trap confirm, no held-out), 51 clean golden, tests/ sweep. 100 controls, seed 42.

| q | safe | calib correct | calib ANSWER | new errors (ANSWER) | must-refuse opened | traps opened | clean |
| ---: | :---: | ---: | ---: | ---: | :--- | ---: | ---: |
| off (shipped) | - | 92/171 | 26/88 | - | d5-38 | 5/18 | 1.000 |
| 0.10 | no | 93/171 | 26/88 | 0 (0) | - | 4/18 | 1.000 |
| 0.20 | no | 90/171 | 25/88 | 3 (1) | - | 2/18 | 1.000 |
| 0.30 | yes | 88/171 | 24/88 | 5 (2) | - | 0/18 | 1.000 |
| 0.40 | no | 83/171 | 21/88 | 10 (5) | - | 0/18 | 1.000 |
| 0.50 | no | 80/171 | 19/88 | 13 (7) | - | 0/18 | 1.000 |

Safe settings: 1 of 5. Chosen: q = 0.30 (candidate).
Chosen new errors: d3-09, d3-27, d4-29, d4-42, d5-02; fixed: d5-38.
