# WordNet noun-sense gate: calibration on clean + dev + dev2 calib (pre-registered)

Rows: 37 calibration rows (15 dev synonym + 22 dev2 calib) plus 51 clean golden; 144 settings; 72 safe.
Flag off: calibration 26/37 correct, ANSWER 6/15, clean 1.000.

| setting | clean | calib correct | calib ANSWER | fail-open | spurious write | new errors | fixed | safe |
| :--- | ---: | ---: | ---: | ---: | ---: | :--- | :--- | :---: |
| lone p1 f0 n1 morphy=off senses=1 | 1.000 | 28/37 | 8/15 | 0 | 0 | - | d2-12, d2-13 | yes |
| lone p1 f0 n1 morphy=off senses=2 | 1.000 | 28/37 | 8/15 | 0 | 0 | - | d2-12, d2-13 | yes |
| lone p1 f0 n1 morphy=off senses=all | 1.000 | 28/37 | 8/15 | 0 | 0 | - | d2-12, d2-13 | yes |
| lone p1 f0 n1 morphy=on senses=1 | 1.000 | 28/37 | 8/15 | 0 | 0 | - | d2-12, d2-13 | yes |
| lone p1 f0 n1 morphy=on senses=2 | 1.000 | 28/37 | 8/15 | 0 | 0 | - | d2-12, d2-13 | yes |
| lone p1 f0 n1 morphy=on senses=all | 1.000 | 28/37 | 8/15 | 0 | 0 | - | d2-12, d2-13 | yes |
| lone p2 f10 n1 morphy=off senses=1 | 1.000 | 28/37 | 8/15 | 0 | 0 | - | d2-12, d2-13 | yes |
| lone p2 f10 n1 morphy=off senses=2 | 1.000 | 28/37 | 8/15 | 0 | 0 | - | d2-12, d2-13 | yes |
| lone p2 f10 n1 morphy=off senses=all | 1.000 | 28/37 | 8/15 | 0 | 0 | - | d2-12, d2-13 | yes |
| lone p2 f10 n1 morphy=on senses=1 | 1.000 | 28/37 | 8/15 | 0 | 0 | - | d2-12, d2-13 | yes |
| lone p2 f10 n1 morphy=on senses=2 | 1.000 | 28/37 | 8/15 | 0 | 0 | - | d2-12, d2-13 | yes |
| lone p2 f10 n1 morphy=on senses=all | 1.000 | 28/37 | 8/15 | 0 | 0 | - | d2-12, d2-13 | yes |
| lone p2 f25 n1 morphy=off senses=1 | 1.000 | 28/37 | 8/15 | 0 | 0 | - | d2-12, d2-13 | yes |
| lone p2 f25 n1 morphy=off senses=2 | 1.000 | 28/37 | 8/15 | 0 | 0 | - | d2-12, d2-13 | yes |
| lone p2 f25 n1 morphy=off senses=all | 1.000 | 28/37 | 8/15 | 0 | 0 | - | d2-12, d2-13 | yes |
| lone p2 f25 n1 morphy=on senses=1 | 1.000 | 28/37 | 8/15 | 0 | 0 | - | d2-12, d2-13 | yes |
| lone p2 f25 n1 morphy=on senses=2 | 1.000 | 28/37 | 8/15 | 0 | 0 | - | d2-12, d2-13 | yes |
| lone p2 f25 n1 morphy=on senses=all | 1.000 | 28/37 | 8/15 | 0 | 0 | - | d2-12, d2-13 | yes |
| lone p1 f0 n2 morphy=off senses=1 | 1.000 | 27/37 | 7/15 | 0 | 0 | - | d2-12 | yes |
| lone p1 f0 n2 morphy=off senses=2 | 1.000 | 27/37 | 7/15 | 0 | 0 | - | d2-12 | yes |
| lone p1 f0 n2 morphy=off senses=all | 1.000 | 27/37 | 7/15 | 0 | 0 | - | d2-12 | yes |
| lone p1 f0 n2 morphy=on senses=1 | 1.000 | 27/37 | 7/15 | 0 | 0 | - | d2-12 | yes |
| lone p1 f0 n2 morphy=on senses=2 | 1.000 | 27/37 | 7/15 | 0 | 0 | - | d2-12 | yes |
| lone p1 f0 n2 morphy=on senses=all | 1.000 | 27/37 | 7/15 | 0 | 0 | - | d2-12 | yes |
| known p0 f0 n1 morphy=off senses=1 | 1.000 | 26/37 | 6/15 | 0 | 0 | - | - | yes |
| known p0 f0 n1 morphy=off senses=2 | 1.000 | 26/37 | 6/15 | 0 | 0 | - | - | yes |
| known p0 f0 n1 morphy=off senses=all | 1.000 | 26/37 | 6/15 | 0 | 0 | - | - | yes |
| known p0 f0 n1 morphy=on senses=1 | 1.000 | 26/37 | 6/15 | 0 | 0 | - | - | yes |
| known p0 f0 n1 morphy=on senses=2 | 1.000 | 26/37 | 6/15 | 0 | 0 | - | - | yes |
| known p0 f0 n1 morphy=on senses=all | 1.000 | 26/37 | 6/15 | 0 | 0 | - | - | yes |
| known p0 f0 n2 morphy=off senses=1 | 1.000 | 26/37 | 6/15 | 0 | 0 | - | - | yes |
| known p0 f0 n2 morphy=off senses=2 | 1.000 | 26/37 | 6/15 | 0 | 0 | - | - | yes |
| known p0 f0 n2 morphy=off senses=all | 1.000 | 26/37 | 6/15 | 0 | 0 | - | - | yes |
| known p0 f0 n2 morphy=on senses=1 | 1.000 | 26/37 | 6/15 | 0 | 0 | - | - | yes |
| known p0 f0 n2 morphy=on senses=2 | 1.000 | 26/37 | 6/15 | 0 | 0 | - | - | yes |
| known p0 f0 n2 morphy=on senses=all | 1.000 | 26/37 | 6/15 | 0 | 0 | - | - | yes |
| known p1 f0 n1 morphy=off senses=1 | 1.000 | 26/37 | 6/15 | 0 | 0 | - | - | yes |
| known p1 f0 n1 morphy=off senses=2 | 1.000 | 26/37 | 6/15 | 0 | 0 | - | - | yes |
| known p1 f0 n1 morphy=off senses=all | 1.000 | 26/37 | 6/15 | 0 | 0 | - | - | yes |
| known p1 f0 n1 morphy=on senses=1 | 1.000 | 26/37 | 6/15 | 0 | 0 | - | - | yes |
| known p1 f0 n1 morphy=on senses=2 | 1.000 | 26/37 | 6/15 | 0 | 0 | - | - | yes |
| known p1 f0 n1 morphy=on senses=all | 1.000 | 26/37 | 6/15 | 0 | 0 | - | - | yes |
| known p1 f0 n2 morphy=off senses=1 | 1.000 | 26/37 | 6/15 | 0 | 0 | - | - | yes |
| known p1 f0 n2 morphy=off senses=2 | 1.000 | 26/37 | 6/15 | 0 | 0 | - | - | yes |
| known p1 f0 n2 morphy=off senses=all | 1.000 | 26/37 | 6/15 | 0 | 0 | - | - | yes |
| known p1 f0 n2 morphy=on senses=1 | 1.000 | 26/37 | 6/15 | 0 | 0 | - | - | yes |
| known p1 f0 n2 morphy=on senses=2 | 1.000 | 26/37 | 6/15 | 0 | 0 | - | - | yes |
| known p1 f0 n2 morphy=on senses=all | 1.000 | 26/37 | 6/15 | 0 | 0 | - | - | yes |
| known p2 f10 n1 morphy=off senses=1 | 1.000 | 26/37 | 6/15 | 0 | 0 | - | - | yes |
| known p2 f10 n1 morphy=off senses=2 | 1.000 | 26/37 | 6/15 | 0 | 0 | - | - | yes |
| known p2 f10 n1 morphy=off senses=all | 1.000 | 26/37 | 6/15 | 0 | 0 | - | - | yes |
| known p2 f10 n1 morphy=on senses=1 | 1.000 | 26/37 | 6/15 | 0 | 0 | - | - | yes |
| known p2 f10 n1 morphy=on senses=2 | 1.000 | 26/37 | 6/15 | 0 | 0 | - | - | yes |
| known p2 f10 n1 morphy=on senses=all | 1.000 | 26/37 | 6/15 | 0 | 0 | - | - | yes |
| known p2 f25 n1 morphy=off senses=1 | 1.000 | 26/37 | 6/15 | 0 | 0 | - | - | yes |
| known p2 f25 n1 morphy=off senses=2 | 1.000 | 26/37 | 6/15 | 0 | 0 | - | - | yes |
| known p2 f25 n1 morphy=off senses=all | 1.000 | 26/37 | 6/15 | 0 | 0 | - | - | yes |
| known p2 f25 n1 morphy=on senses=1 | 1.000 | 26/37 | 6/15 | 0 | 0 | - | - | yes |
| known p2 f25 n1 morphy=on senses=2 | 1.000 | 26/37 | 6/15 | 0 | 0 | - | - | yes |
| known p2 f25 n1 morphy=on senses=all | 1.000 | 26/37 | 6/15 | 0 | 0 | - | - | yes |
| lone p0 f0 n1 morphy=off senses=1 | 1.000 | 26/37 | 6/15 | 0 | 0 | - | - | yes |
| lone p0 f0 n1 morphy=off senses=2 | 1.000 | 26/37 | 6/15 | 0 | 0 | - | - | yes |
| lone p0 f0 n1 morphy=off senses=all | 1.000 | 26/37 | 6/15 | 0 | 0 | - | - | yes |
| lone p0 f0 n1 morphy=on senses=1 | 1.000 | 26/37 | 6/15 | 0 | 0 | - | - | yes |
| lone p0 f0 n1 morphy=on senses=2 | 1.000 | 26/37 | 6/15 | 0 | 0 | - | - | yes |
| lone p0 f0 n1 morphy=on senses=all | 1.000 | 26/37 | 6/15 | 0 | 0 | - | - | yes |
| lone p0 f0 n2 morphy=off senses=1 | 1.000 | 26/37 | 6/15 | 0 | 0 | - | - | yes |
| lone p0 f0 n2 morphy=off senses=2 | 1.000 | 26/37 | 6/15 | 0 | 0 | - | - | yes |
| lone p0 f0 n2 morphy=off senses=all | 1.000 | 26/37 | 6/15 | 0 | 0 | - | - | yes |
| lone p0 f0 n2 morphy=on senses=1 | 1.000 | 26/37 | 6/15 | 0 | 0 | - | - | yes |
| lone p0 f0 n2 morphy=on senses=2 | 1.000 | 26/37 | 6/15 | 0 | 0 | - | - | yes |
| lone p0 f0 n2 morphy=on senses=all | 1.000 | 26/37 | 6/15 | 0 | 0 | - | - | yes |
| all p1 f0 n2 morphy=off senses=1 | 0.941 | 27/37 | 8/15 | 0 | 0 | d2-37 | d2-12, d2-13 | no |
| all p1 f0 n2 morphy=on senses=1 | 0.941 | 27/37 | 8/15 | 0 | 0 | d2-37 | d2-12, d2-13 | no |
| all p2 f10 n2 morphy=off senses=1 | 0.941 | 27/37 | 8/15 | 0 | 0 | d2-37 | d2-12, d2-13 | no |
| all p2 f10 n2 morphy=on senses=1 | 0.941 | 27/37 | 8/15 | 0 | 0 | d2-37 | d2-12, d2-13 | no |
| all p2 f25 n1 morphy=off senses=1 | 0.902 | 27/37 | 8/15 | 0 | 0 | d2-37 | d2-12, d2-13 | no |
| all p2 f25 n1 morphy=on senses=1 | 0.902 | 27/37 | 8/15 | 0 | 0 | d2-37 | d2-12, d2-13 | no |
| all p2 f25 n2 morphy=off senses=1 | 0.902 | 27/37 | 8/15 | 0 | 0 | d2-37 | d2-12, d2-13 | no |
| all p2 f25 n2 morphy=on senses=1 | 0.902 | 27/37 | 8/15 | 0 | 0 | d2-37 | d2-12, d2-13 | no |
| lone p2 f10 n2 morphy=off senses=1 | 0.980 | 27/37 | 7/15 | 0 | 0 | - | d2-12 | no |
| lone p2 f10 n2 morphy=off senses=2 | 0.980 | 27/37 | 7/15 | 0 | 0 | - | d2-12 | no |
| lone p2 f10 n2 morphy=off senses=all | 0.980 | 27/37 | 7/15 | 0 | 0 | - | d2-12 | no |
| lone p2 f10 n2 morphy=on senses=1 | 0.980 | 27/37 | 7/15 | 0 | 0 | - | d2-12 | no |
| lone p2 f10 n2 morphy=on senses=2 | 0.980 | 27/37 | 7/15 | 0 | 0 | - | d2-12 | no |
| lone p2 f10 n2 morphy=on senses=all | 0.980 | 27/37 | 7/15 | 0 | 0 | - | d2-12 | no |
| lone p2 f25 n2 morphy=off senses=1 | 0.980 | 27/37 | 7/15 | 0 | 0 | - | d2-12 | no |
| lone p2 f25 n2 morphy=off senses=2 | 0.980 | 27/37 | 7/15 | 0 | 0 | - | d2-12 | no |
| lone p2 f25 n2 morphy=off senses=all | 0.980 | 27/37 | 7/15 | 0 | 0 | - | d2-12 | no |
| lone p2 f25 n2 morphy=on senses=1 | 0.980 | 27/37 | 7/15 | 0 | 0 | - | d2-12 | no |
| lone p2 f25 n2 morphy=on senses=2 | 0.980 | 27/37 | 7/15 | 0 | 0 | - | d2-12 | no |
| lone p2 f25 n2 morphy=on senses=all | 0.980 | 27/37 | 7/15 | 0 | 0 | - | d2-12 | no |
| all p1 f0 n2 morphy=off senses=2 | 0.922 | 27/37 | 7/15 | 0 | 0 | d2-16 | d2-12, d2-13 | no |
| all p1 f0 n2 morphy=on senses=2 | 0.922 | 27/37 | 7/15 | 0 | 0 | d2-16 | d2-12, d2-13 | no |
| all p1 f0 n1 morphy=off senses=1 | 0.941 | 26/37 | 7/15 | 0 | 0 | d2-37 | d2-12 | no |
| all p1 f0 n1 morphy=on senses=1 | 0.941 | 26/37 | 7/15 | 0 | 0 | d2-37 | d2-12 | no |
| all p2 f10 n1 morphy=off senses=1 | 0.941 | 26/37 | 7/15 | 0 | 0 | d2-37 | d2-12 | no |
| all p2 f10 n1 morphy=on senses=1 | 0.941 | 26/37 | 7/15 | 0 | 0 | d2-37 | d2-12 | no |
| all p2 f25 n1 morphy=off senses=2 | 0.882 | 26/37 | 7/15 | 0 | 0 | d2-16, d2-37 | d2-12, d2-13 | no |
| all p2 f25 n1 morphy=off senses=all | 0.882 | 26/37 | 7/15 | 0 | 0 | d2-16, d2-37 | d2-12, d2-13 | no |
| all p2 f25 n1 morphy=on senses=2 | 0.882 | 26/37 | 7/15 | 0 | 0 | d2-16, d2-37 | d2-12, d2-13 | no |
| known p2 f10 n2 morphy=off senses=1 | 0.980 | 26/37 | 6/15 | 0 | 0 | - | - | no |
| known p2 f10 n2 morphy=off senses=2 | 0.980 | 26/37 | 6/15 | 0 | 0 | - | - | no |
| known p2 f10 n2 morphy=off senses=all | 0.980 | 26/37 | 6/15 | 0 | 0 | - | - | no |
| known p2 f10 n2 morphy=on senses=1 | 0.980 | 26/37 | 6/15 | 0 | 0 | - | - | no |
| known p2 f10 n2 morphy=on senses=2 | 0.980 | 26/37 | 6/15 | 0 | 0 | - | - | no |
| known p2 f10 n2 morphy=on senses=all | 0.980 | 26/37 | 6/15 | 0 | 0 | - | - | no |
| known p2 f25 n2 morphy=off senses=1 | 0.980 | 26/37 | 6/15 | 0 | 0 | - | - | no |
| known p2 f25 n2 morphy=off senses=2 | 0.980 | 26/37 | 6/15 | 0 | 0 | - | - | no |
| known p2 f25 n2 morphy=off senses=all | 0.980 | 26/37 | 6/15 | 0 | 0 | - | - | no |
| known p2 f25 n2 morphy=on senses=1 | 0.980 | 26/37 | 6/15 | 0 | 0 | - | - | no |
| known p2 f25 n2 morphy=on senses=2 | 0.980 | 26/37 | 6/15 | 0 | 0 | - | - | no |
| known p2 f25 n2 morphy=on senses=all | 0.980 | 26/37 | 6/15 | 0 | 0 | - | - | no |
| all p1 f0 n2 morphy=off senses=all | 0.922 | 26/37 | 6/15 | 0 | 0 | d2-16 | d2-12 | no |
| all p2 f10 n2 morphy=off senses=2 | 0.902 | 26/37 | 6/15 | 0 | 0 | d2-16, g03-synonym | d2-12, d2-13 | no |
| all p2 f10 n2 morphy=on senses=2 | 0.902 | 26/37 | 6/15 | 0 | 0 | d2-16, g03-synonym | d2-12, d2-13 | no |
| all p2 f25 n1 morphy=on senses=all | 0.882 | 25/37 | 7/15 | 0 | 0 | d2-16, d2-37, g13-synonym | d2-12, d2-13 | no |
| all p0 f0 n1 morphy=off senses=1 | 0.980 | 25/37 | 6/15 | 0 | 0 | d2-37 | - | no |
| all p0 f0 n1 morphy=off senses=2 | 0.980 | 25/37 | 6/15 | 0 | 0 | d2-37 | - | no |
| all p0 f0 n1 morphy=off senses=all | 0.980 | 25/37 | 6/15 | 0 | 0 | d2-37 | - | no |
| all p0 f0 n1 morphy=on senses=1 | 0.980 | 25/37 | 6/15 | 0 | 0 | d2-37 | - | no |
| all p0 f0 n1 morphy=on senses=2 | 0.980 | 25/37 | 6/15 | 0 | 0 | d2-37 | - | no |
| all p0 f0 n1 morphy=on senses=all | 0.980 | 25/37 | 6/15 | 0 | 0 | d2-37 | - | no |
| all p0 f0 n2 morphy=off senses=1 | 0.980 | 25/37 | 6/15 | 0 | 0 | d2-37 | - | no |
| all p0 f0 n2 morphy=off senses=2 | 0.980 | 25/37 | 6/15 | 0 | 0 | d2-37 | - | no |
| all p0 f0 n2 morphy=off senses=all | 0.980 | 25/37 | 6/15 | 0 | 0 | d2-37 | - | no |
| all p0 f0 n2 morphy=on senses=1 | 0.980 | 25/37 | 6/15 | 0 | 0 | d2-37 | - | no |
| all p0 f0 n2 morphy=on senses=2 | 0.980 | 25/37 | 6/15 | 0 | 0 | d2-37 | - | no |
| all p0 f0 n2 morphy=on senses=all | 0.980 | 25/37 | 6/15 | 0 | 0 | d2-37 | - | no |
| all p1 f0 n1 morphy=off senses=2 | 0.902 | 25/37 | 6/15 | 0 | 0 | d2-16, d2-37 | d2-12 | no |
| all p1 f0 n1 morphy=off senses=all | 0.902 | 25/37 | 6/15 | 0 | 0 | d2-16, d2-37 | d2-12 | no |
| all p1 f0 n1 morphy=on senses=2 | 0.902 | 25/37 | 6/15 | 0 | 0 | d2-16, d2-37 | d2-12 | no |
| all p1 f0 n2 morphy=on senses=all | 0.922 | 25/37 | 6/15 | 0 | 0 | d2-16, g13-synonym | d2-12 | no |
| all p2 f10 n1 morphy=off senses=2 | 0.902 | 25/37 | 6/15 | 0 | 0 | d2-16, d2-37 | d2-12 | no |
| all p2 f10 n1 morphy=off senses=all | 0.902 | 25/37 | 6/15 | 0 | 0 | d2-16, d2-37 | d2-12 | no |
| all p2 f10 n1 morphy=on senses=2 | 0.902 | 25/37 | 6/15 | 0 | 0 | d2-16, d2-37 | d2-12 | no |
| all p2 f25 n2 morphy=off senses=2 | 0.863 | 25/37 | 6/15 | 0 | 0 | d2-16, d2-37, g03-synonym | d2-12, d2-13 | no |
| all p2 f25 n2 morphy=on senses=2 | 0.863 | 25/37 | 6/15 | 0 | 0 | d2-16, d2-37, g03-synonym | d2-12, d2-13 | no |
| all p1 f0 n1 morphy=on senses=all | 0.902 | 24/37 | 6/15 | 0 | 0 | d2-16, d2-37, g13-synonym | d2-12 | no |
| all p2 f10 n1 morphy=on senses=all | 0.902 | 24/37 | 6/15 | 0 | 0 | d2-16, d2-37, g13-synonym | d2-12 | no |
| all p2 f10 n2 morphy=off senses=all | 0.882 | 24/37 | 4/15 | 0 | 0 | d2-06, d2-16, g03-synonym | d2-12 | no |
| all p2 f10 n2 morphy=on senses=all | 0.882 | 23/37 | 4/15 | 0 | 0 | d2-06, d2-16, g03-synonym, g13-synonym | d2-12 | no |
| all p2 f25 n2 morphy=off senses=all | 0.863 | 23/37 | 4/15 | 0 | 0 | d2-06, d2-16, d2-37, g03-synonym | d2-12 | no |
| all p2 f25 n2 morphy=on senses=all | 0.863 | 22/37 | 4/15 | 0 | 0 | d2-06, d2-16, d2-37, g03-synonym, g13-synonym | d2-12 | no |

Chosen: lone p1 f0 n1 morphy=off senses=1 (28/37; off 26/37). Candidate for the confirm run: yes.
