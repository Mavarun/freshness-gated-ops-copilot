# Null-control test on passage rescues: calibration (v1)

Rows: 171 dev5 calibration rows + 18 attribute-trap tune rows (no dev5 confirm, no trap confirm, no held-out), 51 clean golden, tests/ sweep. 100 controls, seed 42.

| q | safe | calib correct | calib ANSWER | new errors (ANSWER) | must-refuse opened | traps opened | clean |
| ---: | :---: | ---: | ---: | ---: | :--- | ---: | ---: |
| off (shipped) | - | 92/171 | 26/88 | - | d5-38 | 5/18 | 1.000 |
| 0.10 | no | 93/171 | 26/88 | 0 (0) | - | 4/18 | 1.000 |
| 0.20 | no | 92/171 | 26/88 | 1 (0) | - | 3/18 | 1.000 |
| 0.30 | no | 91/171 | 26/88 | 2 (0) | - | 2/18 | 1.000 |
| 0.40 | no | 89/171 | 25/88 | 4 (1) | - | 2/18 | 1.000 |
| 0.50 | no | 89/171 | 25/88 | 4 (1) | - | 2/18 | 1.000 |

Safe settings: 0 of 5. Chosen: q = 0.10 (no candidate: ships off).
Chosen new errors: -; fixed: d5-38.
