# WordNet noun-sense calibration (clean golden + dev synonym rows only)

Baseline (off): clean 1.000, dev synonym 0.800 (3/5 dev ANSWER rows).

| scope | max_path | max_fanout | max_neighbours | clean | fail-open | spurious write | dev synonym | dev ANSWER | safe |
| :--- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | :---: |
| known | 0 | 0 | 1 | 1.000 | 0 | 0 | 0.800 | 3/5 | yes |
| known | 0 | 0 | 2 | 1.000 | 0 | 0 | 0.800 | 3/5 | yes |
| known | 1 | 0 | 1 | 1.000 | 0 | 0 | 0.800 | 3/5 | yes |
| known | 1 | 0 | 2 | 1.000 | 0 | 0 | 0.800 | 3/5 | yes |
| known | 2 | 10 | 1 | 1.000 | 0 | 0 | 0.800 | 3/5 | yes |
| known | 2 | 25 | 1 | 1.000 | 0 | 0 | 0.800 | 3/5 | yes |
| known | 2 | 50 | 1 | 1.000 | 0 | 0 | 0.800 | 3/5 | yes |
| known | 2 | 10 | 2 | 0.980 | 0 | 0 | 0.800 | 3/5 | no |
| known | 2 | 25 | 2 | 0.980 | 0 | 0 | 0.800 | 3/5 | no |
| known | 2 | 50 | 2 | 0.980 | 0 | 0 | 0.800 | 3/5 | no |
| all | 0 | 0 | 1 | 0.980 | 0 | 0 | 0.800 | 3/5 | no |
| all | 0 | 0 | 2 | 0.980 | 0 | 0 | 0.800 | 3/5 | no |
| all | 1 | 0 | 1 | 0.902 | 0 | 0 | 0.800 | 3/5 | no |
| all | 1 | 0 | 2 | 0.922 | 0 | 0 | 0.800 | 3/5 | no |
| all | 2 | 10 | 1 | 0.902 | 0 | 0 | 0.800 | 3/5 | no |
| all | 2 | 25 | 1 | 0.882 | 0 | 0 | 0.800 | 3/5 | no |
| all | 2 | 50 | 1 | 0.882 | 0 | 0 | 0.800 | 3/5 | no |
| all | 2 | 10 | 2 | 0.882 | 0 | 0 | 0.733 | 2/5 | no |
| all | 2 | 25 | 2 | 0.863 | 0 | 0 | 0.733 | 2/5 | no |
| all | 2 | 50 | 2 | 0.863 | 0 | 0 | 0.733 | 2/5 | no |

Chosen (safe, then dev accuracy, then most conservative): scope known, max_path 0, max_fanout 0, max_neighbours 1.
