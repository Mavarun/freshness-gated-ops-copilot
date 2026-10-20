# Datamuse means-like gate: calibration on clean + dev + dev2 calib (pre-registered)

Rows: 37 calibration rows (15 dev synonym + 22 dev2 calib) plus 51 clean golden; 60 settings; 28 safe.
Flag off: calibration 26/37 correct, ANSWER 6/15, clean 1.000.

| setting | clean | calib correct | calib ANSWER | fail-open | spurious write | new errors | fixed | safe |
| :--- | ---: | ---: | ---: | ---: | ---: | :--- | :--- | :---: |
| lone rank<=10 n2 noun-only=off | 1.000 | 28/37 | 8/15 | 0 | 0 | - | d2-01, d2-13 | yes |
| lone rank<=10 n2 noun-only=on | 1.000 | 28/37 | 8/15 | 0 | 0 | - | d2-01, d2-13 | yes |
| lone rank<=10 n1 noun-only=off | 1.000 | 27/37 | 7/15 | 0 | 0 | - | d2-13 | yes |
| lone rank<=10 n1 noun-only=on | 1.000 | 27/37 | 7/15 | 0 | 0 | - | d2-13 | yes |
| known rank<=10 n1 noun-only=off | 1.000 | 26/37 | 6/15 | 0 | 0 | - | - | yes |
| known rank<=3 n1 noun-only=off | 1.000 | 26/37 | 6/15 | 0 | 0 | - | - | yes |
| known rank<=5 n1 noun-only=off | 1.000 | 26/37 | 6/15 | 0 | 0 | - | - | yes |
| known rank<=10 n1 noun-only=on | 1.000 | 26/37 | 6/15 | 0 | 0 | - | - | yes |
| known rank<=10 n2 noun-only=off | 1.000 | 26/37 | 6/15 | 0 | 0 | - | - | yes |
| known rank<=3 n1 noun-only=on | 1.000 | 26/37 | 6/15 | 0 | 0 | - | - | yes |
| known rank<=3 n2 noun-only=off | 1.000 | 26/37 | 6/15 | 0 | 0 | - | - | yes |
| known rank<=5 n1 noun-only=on | 1.000 | 26/37 | 6/15 | 0 | 0 | - | - | yes |
| known rank<=5 n2 noun-only=off | 1.000 | 26/37 | 6/15 | 0 | 0 | - | - | yes |
| known rank<=10 n2 noun-only=on | 1.000 | 26/37 | 6/15 | 0 | 0 | - | - | yes |
| known rank<=3 n2 noun-only=on | 1.000 | 26/37 | 6/15 | 0 | 0 | - | - | yes |
| known rank<=5 n2 noun-only=on | 1.000 | 26/37 | 6/15 | 0 | 0 | - | - | yes |
| lone rank<=3 n1 noun-only=off | 1.000 | 26/37 | 6/15 | 0 | 0 | - | - | yes |
| lone rank<=5 n1 noun-only=off | 1.000 | 26/37 | 6/15 | 0 | 0 | - | - | yes |
| lone rank<=3 n1 noun-only=on | 1.000 | 26/37 | 6/15 | 0 | 0 | - | - | yes |
| lone rank<=3 n2 noun-only=off | 1.000 | 26/37 | 6/15 | 0 | 0 | - | - | yes |
| lone rank<=5 n1 noun-only=on | 1.000 | 26/37 | 6/15 | 0 | 0 | - | - | yes |
| lone rank<=5 n2 noun-only=off | 1.000 | 26/37 | 6/15 | 0 | 0 | - | - | yes |
| lone rank<=3 n2 noun-only=on | 1.000 | 26/37 | 6/15 | 0 | 0 | - | - | yes |
| lone rank<=5 n2 noun-only=on | 1.000 | 26/37 | 6/15 | 0 | 0 | - | - | yes |
| all rank<=3 n1 noun-only=off | 1.000 | 26/37 | 6/15 | 0 | 0 | - | - | yes |
| all rank<=3 n1 noun-only=on | 1.000 | 26/37 | 6/15 | 0 | 0 | - | - | yes |
| all rank<=3 n2 noun-only=off | 1.000 | 26/37 | 6/15 | 0 | 0 | - | - | yes |
| all rank<=3 n2 noun-only=on | 1.000 | 26/37 | 6/15 | 0 | 0 | - | - | yes |
| lone rank<=20 n2 noun-only=off | 0.980 | 29/37 | 9/15 | 0 | 0 | - | d2-01, d2-12, d2-13 | no |
| lone rank<=50 n2 noun-only=off | 0.980 | 29/37 | 9/15 | 0 | 0 | - | d2-01, d2-03, d2-13 | no |
| lone rank<=20 n2 noun-only=on | 0.980 | 29/37 | 9/15 | 0 | 0 | - | d2-01, d2-12, d2-13 | no |
| lone rank<=50 n2 noun-only=on | 0.980 | 29/37 | 9/15 | 0 | 0 | - | d2-01, d2-03, d2-13 | no |
| lone rank<=20 n1 noun-only=off | 0.980 | 28/37 | 8/15 | 0 | 0 | - | d2-12, d2-13 | no |
| lone rank<=50 n1 noun-only=off | 0.980 | 28/37 | 8/15 | 0 | 0 | - | d2-12, d2-13 | no |
| lone rank<=20 n1 noun-only=on | 0.980 | 28/37 | 8/15 | 0 | 0 | - | d2-12, d2-13 | no |
| lone rank<=50 n1 noun-only=on | 0.980 | 28/37 | 8/15 | 0 | 0 | - | d2-12, d2-13 | no |
| all rank<=20 n1 noun-only=off | 0.863 | 27/37 | 8/15 | 0 | 0 | d2-06, d2-37 | d2-12, d2-13, g24-synonym | no |
| all rank<=20 n1 noun-only=on | 0.863 | 27/37 | 8/15 | 0 | 0 | d2-06, d2-37 | d2-12, d2-13, g24-synonym | no |
| all rank<=50 n2 noun-only=off | 0.824 | 26/37 | 7/15 | 1 | 0 | d2-16, d2-37 | d2-03, g24-synonym | no |
| known rank<=20 n1 noun-only=off | 0.980 | 26/37 | 6/15 | 0 | 0 | - | - | no |
| known rank<=50 n1 noun-only=off | 0.980 | 26/37 | 6/15 | 0 | 0 | - | - | no |
| known rank<=20 n1 noun-only=on | 0.980 | 26/37 | 6/15 | 0 | 0 | - | - | no |
| known rank<=20 n2 noun-only=off | 0.980 | 26/37 | 6/15 | 0 | 0 | - | - | no |
| known rank<=50 n1 noun-only=on | 0.980 | 26/37 | 6/15 | 0 | 0 | - | - | no |
| known rank<=50 n2 noun-only=off | 0.980 | 26/37 | 6/15 | 0 | 0 | - | - | no |
| known rank<=20 n2 noun-only=on | 0.980 | 26/37 | 6/15 | 0 | 0 | - | - | no |
| known rank<=50 n2 noun-only=on | 0.980 | 26/37 | 6/15 | 0 | 0 | - | - | no |
| all rank<=50 n1 noun-only=off | 0.863 | 25/37 | 7/15 | 0 | 0 | d2-06, d2-37, g13-synonym | d2-13, g24-synonym | no |
| all rank<=10 n1 noun-only=off | 0.961 | 25/37 | 6/15 | 0 | 0 | d2-06, d2-37 | d2-13 | no |
| all rank<=5 n1 noun-only=off | 0.980 | 25/37 | 6/15 | 0 | 0 | d2-37 | - | no |
| all rank<=10 n1 noun-only=on | 0.961 | 25/37 | 6/15 | 0 | 0 | d2-06, d2-37 | d2-13 | no |
| all rank<=5 n1 noun-only=on | 0.980 | 25/37 | 6/15 | 0 | 0 | d2-37 | - | no |
| all rank<=5 n2 noun-only=off | 0.980 | 25/37 | 6/15 | 0 | 0 | d2-37 | - | no |
| all rank<=20 n2 noun-only=off | 0.824 | 25/37 | 6/15 | 1 | 0 | d2-06, d2-16, d2-37 | d2-12, g24-synonym | no |
| all rank<=5 n2 noun-only=on | 0.980 | 25/37 | 6/15 | 0 | 0 | d2-37 | - | no |
| all rank<=20 n2 noun-only=on | 0.824 | 25/37 | 6/15 | 1 | 0 | d2-06, d2-16, d2-37 | d2-12, g24-synonym | no |
| all rank<=50 n2 noun-only=on | 0.824 | 25/37 | 6/15 | 1 | 0 | d2-06, d2-16, d2-37 | d2-03, g24-synonym | no |
| all rank<=50 n1 noun-only=on | 0.863 | 24/37 | 6/15 | 0 | 0 | d2-06, d2-37, g13-synonym | g24-synonym | no |
| all rank<=10 n2 noun-only=off | 0.961 | 24/37 | 5/15 | 0 | 0 | d2-06, d2-37 | - | no |
| all rank<=10 n2 noun-only=on | 0.961 | 24/37 | 5/15 | 0 | 0 | d2-06, d2-37 | - | no |

Chosen: lone rank<=10 n2 noun-only=off (28/37; off 26/37). Candidate for the confirm run: yes.
