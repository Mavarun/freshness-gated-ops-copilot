# Unknown-words-only Datamuse: calibration on dev + dev2 + dev3 + dev4 tune (pre-registered)

Rows: 126 calibration rows (15 dev synonym, 43 dev2, 45 dev3, 23 dev4 tune) plus 51 clean golden and the tests/ literal sweep; 24 settings (scope lone, expand_known off); 13 safe.
Flag off: calibration 75/126 correct, ANSWER 21/62, clean 1.000. context>=0 means the gate is off.

| setting | clean | calib correct | calib ANSWER | fail-open | spurious write | new errors | must-refuse opened | sweep opened (labelled) | fixed | safe |
| :--- | ---: | ---: | ---: | ---: | ---: | :--- | :--- | :--- | :--- | :---: |
| rank<=100 n2 context>=2 | 1.000 | 84/126 | 29/62 | 0 | 0 | - | - | 3 (0) | d2-01, d2-03, d2-18, d2-19, d2-21, d3-04, d3-13, d3-14, d4-22 | yes |
| rank<=100 n1 context>=2 | 1.000 | 83/126 | 28/62 | 0 | 0 | - | - | 2 (0) | d2-03, d2-18, d2-19, d2-21, d3-04, d3-13, d3-14, d4-22 | yes |
| rank<=50 n2 context>=2 | 1.000 | 83/126 | 28/62 | 0 | 0 | - | - | 3 (0) | d2-01, d2-03, d2-19, d2-21, d3-04, d3-13, d3-14, d4-22 | yes |
| rank<=20 n2 context>=0 | 1.000 | 83/126 | 27/62 | 0 | 0 | - | - | 2 (0) | d2-01, d2-12, d2-13, d2-18, d2-21, d2-26, d4-06, d4-17 | yes |
| rank<=50 n1 context>=2 | 1.000 | 82/126 | 27/62 | 0 | 0 | - | - | 2 (0) | d2-03, d2-19, d2-21, d3-04, d3-13, d3-14, d4-22 | yes |
| rank<=20 n2 context>=1 | 1.000 | 81/126 | 25/62 | 0 | 0 | - | - | 2 (0) | d2-01, d2-13, d2-21, d2-26, d4-06, d4-17 | yes |
| rank<=10 n2 context>=1 | 1.000 | 80/126 | 24/62 | 0 | 0 | - | - | 2 (0) | d2-01, d2-13, d2-21, d2-26, d4-17 | yes |
| rank<=20 n1 context>=1 | 1.000 | 80/126 | 24/62 | 0 | 0 | - | - | 0 (0) | d2-13, d2-21, d2-26, d4-06, d4-17 | yes |
| rank<=10 n1 context>=1 | 1.000 | 79/126 | 23/62 | 0 | 0 | - | - | 0 (0) | d2-13, d2-21, d2-26, d4-17 | yes |
| rank<=10 n2 context>=2 | 1.000 | 77/126 | 22/62 | 0 | 0 | - | - | 1 (0) | d2-01, d2-21 | yes |
| rank<=20 n2 context>=2 | 1.000 | 77/126 | 22/62 | 0 | 0 | - | - | 1 (0) | d2-01, d2-21 | yes |
| rank<=10 n1 context>=2 | 1.000 | 76/126 | 21/62 | 0 | 0 | - | - | 0 (0) | d2-21 | yes |
| rank<=20 n1 context>=2 | 1.000 | 76/126 | 21/62 | 0 | 0 | - | - | 0 (0) | d2-21 | yes |
| rank<=100 n2 context>=1 | 1.000 | 86/126 | 32/62 | 1 | 0 | d3-33, d3-37 | d3-33 | 8 (0) | d2-01, d2-03, d2-13, d2-18, d2-19, d2-21, d2-26, d3-04, d3-13, d3-14, d4-06, d4-17, d4-22 | no |
| rank<=50 n2 context>=1 | 1.000 | 86/126 | 31/62 | 1 | 0 | d3-33 | d3-33 | 7 (0) | d2-01, d2-03, d2-13, d2-19, d2-21, d2-26, d3-04, d3-13, d3-14, d4-06, d4-17, d4-22 | no |
| rank<=100 n1 context>=1 | 1.000 | 85/126 | 31/62 | 1 | 0 | d3-33, d3-37 | d3-33 | 6 (0) | d2-03, d2-13, d2-18, d2-19, d2-21, d2-26, d3-04, d3-13, d3-14, d4-06, d4-17, d4-22 | no |
| rank<=50 n1 context>=1 | 1.000 | 85/126 | 30/62 | 1 | 0 | d3-33 | d3-33 | 5 (0) | d2-03, d2-13, d2-19, d2-21, d2-26, d3-04, d3-13, d3-14, d4-06, d4-17, d4-22 | no |
| rank<=50 n2 context>=0 | 1.000 | 84/126 | 29/62 | 1 | 0 | d3-33 | d3-33 | 7 (0) | d2-01, d2-03, d2-13, d2-21, d2-26, d3-04, d3-13, d3-14, d4-06, d4-17 | no |
| rank<=50 n1 context>=0 | 1.000 | 83/126 | 29/62 | 1 | 0 | d3-33, d3-39 | d3-33 | 2 (0) | d2-12, d2-13, d2-18, d2-21, d2-26, d3-04, d3-13, d3-14, d4-06, d4-17 | no |
| rank<=100 n2 context>=0 | 1.000 | 83/126 | 29/62 | 1 | 0 | d3-33, d3-37 | d3-33 | 7 (0) | d2-01, d2-03, d2-13, d2-21, d2-26, d3-04, d3-13, d3-14, d4-06, d4-17 | no |
| rank<=100 n1 context>=0 | 1.000 | 82/126 | 29/62 | 1 | 0 | d3-33, d3-37, d3-39 | d3-33 | 2 (0) | d2-12, d2-13, d2-18, d2-21, d2-26, d3-04, d3-13, d3-14, d4-06, d4-17 | no |
| rank<=20 n1 context>=0 | 1.000 | 81/126 | 26/62 | 0 | 0 | d3-39 | - | 0 (0) | d2-12, d2-13, d2-18, d2-21, d2-26, d4-06, d4-17 | no |
| rank<=10 n2 context>=0 | 1.000 | 80/126 | 25/62 | 0 | 0 | d3-39 | - | 2 (0) | d2-01, d2-13, d2-18, d2-21, d2-26, d4-17 | no |
| rank<=10 n1 context>=0 | 1.000 | 79/126 | 24/62 | 0 | 0 | d3-39 | - | 0 (0) | d2-13, d2-18, d2-21, d2-26, d4-17 | no |

Chosen: rank<=100 n2 context>=2 (84/126; off 75/126). Candidate for the confirm run: yes.
