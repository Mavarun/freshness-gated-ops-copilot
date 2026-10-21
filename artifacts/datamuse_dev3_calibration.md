# Context-gated Datamuse: calibration on dev + dev2 + dev3 calib (pre-registered)

Rows: 83 calibration rows (15 dev synonym, 43 dev2, 25 dev3 calib) plus 51 clean golden; 48 settings; 5 safe.
Flag off: calibration 55/83 correct, ANSWER 17/38, clean 1.000. context>=0 means the gate is off.

| setting | clean | calib correct | calib ANSWER | fail-open | spurious write | new errors | fixed | safe |
| :--- | ---: | ---: | ---: | ---: | ---: | :--- | :--- | :---: |
| lone rank<=50 n2 context>=2 | 1.000 | 62/83 | 22/38 | 0 | 0 | - | d2-01, d2-03, d2-18, d2-19, d2-21, d3-13, d3-26 | yes |
| lone rank<=100 n2 context>=2 | 1.000 | 62/83 | 22/38 | 0 | 0 | - | d2-01, d2-03, d2-18, d2-19, d2-21, d3-13, d3-26 | yes |
| lone rank<=50 n1 context>=2 | 1.000 | 61/83 | 21/38 | 0 | 0 | - | d2-03, d2-18, d2-19, d2-21, d3-13, d3-26 | yes |
| lone rank<=100 n1 context>=2 | 1.000 | 61/83 | 21/38 | 0 | 0 | - | d2-03, d2-18, d2-19, d2-21, d3-13, d3-26 | yes |
| known rank<=10 n1 context>=0 | 1.000 | 55/83 | 17/38 | 0 | 0 | - | - | yes |
| lone rank<=50 n2 context>=1 | 0.980 | 64/83 | 23/38 | 0 | 0 | - | d2-01, d2-03, d2-13, d2-18, d2-19, d2-21, d2-26, d3-13, d3-26 | no |
| lone rank<=100 n2 context>=1 | 0.980 | 64/83 | 23/38 | 0 | 0 | - | d2-01, d2-03, d2-13, d2-18, d2-19, d2-21, d2-26, d3-13, d3-26 | no |
| lone rank<=50 n1 context>=1 | 0.980 | 63/83 | 22/38 | 0 | 0 | - | d2-03, d2-13, d2-18, d2-19, d2-21, d2-26, d3-13, d3-26 | no |
| lone rank<=100 n1 context>=1 | 0.980 | 63/83 | 22/38 | 0 | 0 | - | d2-03, d2-13, d2-18, d2-19, d2-21, d2-26, d3-13, d3-26 | no |
| lone rank<=50 n1 context>=0 | 0.980 | 60/83 | 21/38 | 0 | 0 | d3-39 | d2-12, d2-13, d2-18, d2-21, d2-26, d3-13 | no |
| lone rank<=100 n1 context>=0 | 0.980 | 60/83 | 21/38 | 0 | 0 | d3-39 | d2-12, d2-13, d2-18, d2-21, d2-26, d3-13 | no |
| lone rank<=20 n2 context>=0 | 0.980 | 60/83 | 20/38 | 0 | 0 | d2-17 | d2-01, d2-12, d2-13, d2-18, d2-21, d2-26 | no |
| lone rank<=50 n2 context>=0 | 0.980 | 60/83 | 20/38 | 0 | 0 | d2-17 | d2-01, d2-03, d2-13, d2-21, d2-26, d3-13 | no |
| lone rank<=100 n2 context>=0 | 0.980 | 60/83 | 20/38 | 0 | 0 | d2-17 | d2-01, d2-03, d2-13, d2-21, d2-26, d3-13 | no |
| lone rank<=20 n1 context>=0 | 0.980 | 59/83 | 20/38 | 0 | 0 | d3-39 | d2-12, d2-13, d2-18, d2-21, d2-26 | no |
| lone rank<=10 n1 context>=0 | 1.000 | 58/83 | 19/38 | 0 | 0 | d3-39 | d2-13, d2-18, d2-21, d2-26 | no |
| lone rank<=10 n2 context>=0 | 1.000 | 58/83 | 19/38 | 0 | 0 | d2-17, d3-39 | d2-01, d2-13, d2-18, d2-21, d2-26 | no |
| lone rank<=10 n2 context>=1 | 1.000 | 58/83 | 18/38 | 0 | 0 | d2-17 | d2-01, d2-13, d2-21, d2-26 | no |
| lone rank<=20 n2 context>=1 | 0.980 | 58/83 | 18/38 | 0 | 0 | d2-17 | d2-01, d2-13, d2-21, d2-26 | no |
| lone rank<=10 n1 context>=1 | 1.000 | 57/83 | 17/38 | 0 | 0 | d2-17 | d2-13, d2-21, d2-26 | no |
| lone rank<=20 n1 context>=1 | 0.980 | 57/83 | 17/38 | 0 | 0 | d2-17 | d2-13, d2-21, d2-26 | no |
| lone rank<=10 n2 context>=2 | 1.000 | 56/83 | 17/38 | 0 | 0 | d2-17 | d2-01, d2-21 | no |
| lone rank<=20 n2 context>=2 | 1.000 | 56/83 | 17/38 | 0 | 0 | d2-17 | d2-01, d2-21 | no |
| known rank<=20 n1 context>=0 | 0.980 | 55/83 | 17/38 | 0 | 0 | - | - | no |
| known rank<=50 n1 context>=0 | 0.980 | 55/83 | 17/38 | 0 | 0 | - | - | no |
| known rank<=100 n1 context>=0 | 0.980 | 55/83 | 17/38 | 0 | 0 | - | - | no |
| known rank<=50 n1 context>=2 | 1.000 | 55/83 | 16/38 | 0 | 0 | d2-17 | d3-26 | no |
| known rank<=50 n1 context>=1 | 0.980 | 55/83 | 16/38 | 0 | 0 | d2-17 | d3-26 | no |
| known rank<=100 n1 context>=2 | 1.000 | 55/83 | 16/38 | 0 | 0 | d2-17 | d3-26 | no |
| known rank<=100 n1 context>=1 | 0.980 | 55/83 | 16/38 | 0 | 0 | d2-17 | d3-26 | no |
| known rank<=50 n2 context>=2 | 1.000 | 55/83 | 16/38 | 0 | 0 | d2-17 | d3-26 | no |
| known rank<=50 n2 context>=1 | 0.980 | 55/83 | 16/38 | 0 | 0 | d2-17 | d3-26 | no |
| known rank<=100 n2 context>=2 | 1.000 | 55/83 | 16/38 | 0 | 0 | d2-17 | d3-26 | no |
| known rank<=100 n2 context>=1 | 0.980 | 55/83 | 16/38 | 0 | 0 | d2-17 | d3-26 | no |
| lone rank<=10 n1 context>=2 | 1.000 | 55/83 | 16/38 | 0 | 0 | d2-17 | d2-21 | no |
| lone rank<=20 n1 context>=2 | 1.000 | 55/83 | 16/38 | 0 | 0 | d2-17 | d2-21 | no |
| known rank<=10 n1 context>=2 | 1.000 | 54/83 | 16/38 | 0 | 0 | d2-17 | - | no |
| known rank<=10 n1 context>=1 | 1.000 | 54/83 | 16/38 | 0 | 0 | d2-17 | - | no |
| known rank<=10 n2 context>=0 | 1.000 | 54/83 | 16/38 | 0 | 0 | d2-17 | - | no |
| known rank<=10 n2 context>=2 | 1.000 | 54/83 | 16/38 | 0 | 0 | d2-17 | - | no |
| known rank<=10 n2 context>=1 | 1.000 | 54/83 | 16/38 | 0 | 0 | d2-17 | - | no |
| known rank<=20 n1 context>=2 | 1.000 | 54/83 | 16/38 | 0 | 0 | d2-17 | - | no |
| known rank<=20 n1 context>=1 | 0.980 | 54/83 | 16/38 | 0 | 0 | d2-17 | - | no |
| known rank<=20 n2 context>=0 | 0.980 | 54/83 | 16/38 | 0 | 0 | d2-17 | - | no |
| known rank<=50 n2 context>=0 | 0.980 | 54/83 | 16/38 | 0 | 0 | d2-17 | - | no |
| known rank<=100 n2 context>=0 | 0.980 | 54/83 | 16/38 | 0 | 0 | d2-17 | - | no |
| known rank<=20 n2 context>=2 | 1.000 | 54/83 | 16/38 | 0 | 0 | d2-17 | - | no |
| known rank<=20 n2 context>=1 | 0.980 | 54/83 | 16/38 | 0 | 0 | d2-17 | - | no |

Chosen: lone rank<=50 n2 context>=2 (62/83; off 55/83). Candidate for the confirm run: yes.
