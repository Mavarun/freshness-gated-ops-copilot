# Word-meaning-gated Datamuse: calibration on dev + dev2 + dev3 + dev4 + dev5 tune (pre-registered)

Rows: 171 calibration rows (15 dev synonym, 43 dev2, 45 dev3, 44 dev4, 24 dev5 tune) plus 51 clean golden and the tests/ literal sweep; 48 settings (scope lone, expand_known off, sense gate on); 0 safe.
Flag off: calibration 92/171 correct, ANSWER 26/88, clean 1.000, fail-open 1. context>=0 means the gate is off.
Must-refuse rows the shipped default (flag off) already answers: d5-38. The safety rule counts every fail-open, so such a row makes every arm unsafe.

| setting | clean | calib correct | calib ANSWER | fail-open | spurious write | new errors | must-refuse opened | sweep opened (labelled) | fixed | safe |
| :--- | ---: | ---: | ---: | ---: | ---: | :--- | :--- | :--- | :--- | :---: |
| rank<=100 n1 context>=2 sense>=0.30 | 1.000 | 101/171 | 34/88 | 1 | 0 | - | - | 0 (0) | d2-03, d2-18, d2-19, d3-04, d3-13, d4-12, d4-19, d4-22, d5-42 | no |
| rank<=100 n2 context>=2 sense>=0.30 | 1.000 | 101/171 | 34/88 | 1 | 0 | - | - | 0 (0) | d2-03, d2-18, d2-19, d3-04, d3-13, d4-12, d4-19, d4-22, d5-42 | no |
| rank<=100 n2 context>=0 sense>=0.30 | 1.000 | 100/171 | 33/88 | 2 | 0 | d3-33 | d3-33 | 0 (0) | d2-03, d2-13, d2-26, d3-04, d3-13, d4-06, d4-19, d4-22, d5-42 | no |
| rank<=50 n2 context>=0 sense>=0.30 | 1.000 | 100/171 | 32/88 | 1 | 0 | - | - | 0 (0) | d2-03, d2-13, d2-26, d3-04, d3-13, d4-06, d4-22, d5-42 | no |
| rank<=100 n2 context>=0 sense>=0.40 | 1.000 | 99/171 | 32/88 | 2 | 0 | d3-33 | d3-33 | 0 (0) | d2-03, d2-13, d2-26, d3-04, d4-06, d4-19, d4-22, d5-42 | no |
| rank<=50 n1 context>=2 sense>=0.30 | 1.000 | 99/171 | 32/88 | 1 | 0 | - | - | 0 (0) | d2-03, d2-19, d3-04, d3-13, d4-12, d4-22, d5-42 | no |
| rank<=50 n2 context>=2 sense>=0.30 | 1.000 | 99/171 | 32/88 | 1 | 0 | - | - | 0 (0) | d2-03, d2-19, d3-04, d3-13, d4-12, d4-22, d5-42 | no |
| rank<=50 n2 context>=0 sense>=0.40 | 1.000 | 99/171 | 31/88 | 1 | 0 | - | - | 0 (0) | d2-03, d2-13, d2-26, d3-04, d4-06, d4-22, d5-42 | no |
| rank<=100 n2 context>=0 sense>=0.60 | 1.000 | 98/171 | 31/88 | 1 | 0 | - | - | 0 (0) | d2-13, d2-18, d3-04, d4-19, d4-22, d5-42 | no |
| rank<=100 n1 context>=2 sense>=0.40 | 1.000 | 98/171 | 31/88 | 1 | 0 | - | - | 0 (0) | d2-03, d2-18, d3-04, d4-19, d4-22, d5-42 | no |
| rank<=100 n2 context>=2 sense>=0.40 | 1.000 | 98/171 | 31/88 | 1 | 0 | - | - | 0 (0) | d2-03, d2-18, d3-04, d4-19, d4-22, d5-42 | no |
| rank<=100 n2 context>=0 sense>=0.50 | 1.000 | 97/171 | 31/88 | 2 | 0 | d3-33 | d3-33 | 0 (0) | d2-13, d2-18, d3-04, d4-19, d4-22, d5-42 | no |
| rank<=100 n1 context>=2 sense>=0.60 | 1.000 | 97/171 | 30/88 | 1 | 0 | - | - | 0 (0) | d2-18, d3-04, d4-19, d4-22, d5-42 | no |
| rank<=100 n1 context>=0 sense>=0.60 | 1.000 | 97/171 | 30/88 | 1 | 0 | - | - | 0 (0) | d2-13, d2-18, d3-04, d4-19, d5-42 | no |
| rank<=100 n2 context>=2 sense>=0.60 | 1.000 | 97/171 | 30/88 | 1 | 0 | - | - | 0 (0) | d2-18, d3-04, d4-19, d4-22, d5-42 | no |
| rank<=100 n1 context>=2 sense>=0.50 | 1.000 | 97/171 | 30/88 | 1 | 0 | - | - | 0 (0) | d2-18, d3-04, d4-19, d4-22, d5-42 | no |
| rank<=100 n2 context>=2 sense>=0.50 | 1.000 | 97/171 | 30/88 | 1 | 0 | - | - | 0 (0) | d2-18, d3-04, d4-19, d4-22, d5-42 | no |
| rank<=100 n1 context>=0 sense>=0.40 | 1.000 | 97/171 | 30/88 | 2 | 0 | d3-33 | d3-33 | 0 (0) | d2-13, d2-26, d3-04, d4-06, d4-19, d5-42 | no |
| rank<=100 n1 context>=0 sense>=0.30 | 1.000 | 97/171 | 30/88 | 2 | 0 | d3-33 | d3-33 | 0 (0) | d2-26, d3-04, d3-13, d4-06, d4-19, d5-42 | no |
| rank<=50 n1 context>=0 sense>=0.40 | 1.000 | 97/171 | 29/88 | 1 | 0 | - | - | 0 (0) | d2-13, d2-26, d3-04, d4-06, d5-42 | no |
| rank<=50 n1 context>=0 sense>=0.30 | 1.000 | 97/171 | 29/88 | 1 | 0 | - | - | 0 (0) | d2-26, d3-04, d3-13, d4-06, d5-42 | no |
| rank<=100 n1 context>=0 sense>=0.50 | 1.000 | 96/171 | 30/88 | 2 | 0 | d3-33 | d3-33 | 0 (0) | d2-13, d2-18, d3-04, d4-19, d5-42 | no |
| rank<=50 n2 context>=0 sense>=0.60 | 1.000 | 96/171 | 29/88 | 1 | 0 | - | - | 0 (0) | d2-13, d3-04, d4-22, d5-42 | no |
| rank<=50 n2 context>=0 sense>=0.50 | 1.000 | 96/171 | 29/88 | 1 | 0 | - | - | 0 (0) | d2-13, d3-04, d4-22, d5-42 | no |
| rank<=50 n1 context>=2 sense>=0.40 | 1.000 | 96/171 | 29/88 | 1 | 0 | - | - | 0 (0) | d2-03, d3-04, d4-22, d5-42 | no |
| rank<=50 n2 context>=2 sense>=0.40 | 1.000 | 96/171 | 29/88 | 1 | 0 | - | - | 0 (0) | d2-03, d3-04, d4-22, d5-42 | no |
| rank<=20 n1 context>=0 sense>=0.40 | 1.000 | 96/171 | 28/88 | 1 | 0 | - | - | 0 (0) | d2-13, d2-26, d4-06, d5-42 | no |
| rank<=20 n2 context>=0 sense>=0.40 | 1.000 | 96/171 | 28/88 | 1 | 0 | - | - | 0 (0) | d2-13, d2-26, d4-06, d5-42 | no |
| rank<=20 n2 context>=0 sense>=0.30 | 1.000 | 96/171 | 28/88 | 1 | 0 | - | - | 0 (0) | d2-13, d2-26, d4-06, d5-42 | no |
| rank<=50 n1 context>=2 sense>=0.60 | 1.000 | 95/171 | 28/88 | 1 | 0 | - | - | 0 (0) | d3-04, d4-22, d5-42 | no |
| rank<=50 n1 context>=0 sense>=0.60 | 1.000 | 95/171 | 28/88 | 1 | 0 | - | - | 0 (0) | d2-13, d3-04, d5-42 | no |
| rank<=50 n2 context>=2 sense>=0.60 | 1.000 | 95/171 | 28/88 | 1 | 0 | - | - | 0 (0) | d3-04, d4-22, d5-42 | no |
| rank<=50 n1 context>=2 sense>=0.50 | 1.000 | 95/171 | 28/88 | 1 | 0 | - | - | 0 (0) | d3-04, d4-22, d5-42 | no |
| rank<=50 n1 context>=0 sense>=0.50 | 1.000 | 95/171 | 28/88 | 1 | 0 | - | - | 0 (0) | d2-13, d3-04, d5-42 | no |
| rank<=50 n2 context>=2 sense>=0.50 | 1.000 | 95/171 | 28/88 | 1 | 0 | - | - | 0 (0) | d3-04, d4-22, d5-42 | no |
| rank<=20 n1 context>=0 sense>=0.30 | 1.000 | 95/171 | 27/88 | 1 | 0 | - | - | 0 (0) | d2-26, d4-06, d5-42 | no |
| rank<=20 n1 context>=0 sense>=0.60 | 1.000 | 94/171 | 27/88 | 1 | 0 | - | - | 0 (0) | d2-13, d5-42 | no |
| rank<=20 n2 context>=0 sense>=0.60 | 1.000 | 94/171 | 27/88 | 1 | 0 | - | - | 0 (0) | d2-13, d5-42 | no |
| rank<=20 n1 context>=0 sense>=0.50 | 1.000 | 94/171 | 27/88 | 1 | 0 | - | - | 0 (0) | d2-13, d5-42 | no |
| rank<=20 n2 context>=0 sense>=0.50 | 1.000 | 94/171 | 27/88 | 1 | 0 | - | - | 0 (0) | d2-13, d5-42 | no |
| rank<=20 n1 context>=2 sense>=0.60 | 1.000 | 93/171 | 26/88 | 1 | 0 | - | - | 0 (0) | d5-42 | no |
| rank<=20 n2 context>=2 sense>=0.60 | 1.000 | 93/171 | 26/88 | 1 | 0 | - | - | 0 (0) | d5-42 | no |
| rank<=20 n1 context>=2 sense>=0.50 | 1.000 | 93/171 | 26/88 | 1 | 0 | - | - | 0 (0) | d5-42 | no |
| rank<=20 n2 context>=2 sense>=0.50 | 1.000 | 93/171 | 26/88 | 1 | 0 | - | - | 0 (0) | d5-42 | no |
| rank<=20 n1 context>=2 sense>=0.40 | 1.000 | 93/171 | 26/88 | 1 | 0 | - | - | 0 (0) | d5-42 | no |
| rank<=20 n2 context>=2 sense>=0.40 | 1.000 | 93/171 | 26/88 | 1 | 0 | - | - | 0 (0) | d5-42 | no |
| rank<=20 n1 context>=2 sense>=0.30 | 1.000 | 93/171 | 26/88 | 1 | 0 | - | - | 0 (0) | d5-42 | no |
| rank<=20 n2 context>=2 sense>=0.30 | 1.000 | 93/171 | 26/88 | 1 | 0 | - | - | 0 (0) | d5-42 | no |

Chosen: rank<=100 n1 context>=2 sense>=0.30 (101/171; off 92/171). Candidate for the confirm run: no.
