# Swap null control, calibration (golden + dev2-dev6)

272 rows; 384 swaps (3 random corpus words per salient term of every row the shipped default answers, seed 1107). Mechanism columns count passed swaps by what supported the swapped-in word.

| arm | swaps | passed | pass rate | passage | translation | semantic | lexical | unsupported | ANSWER kept | lost | must-refuse opened |
| :--- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `shipped` | 384 | 123 | 0.320 | 92 | 0 | 0 | 21 | 10 | 36/133 | 0 | 3/128 |
| `known_off` | 384 | 42 | 0.109 | 0 | 0 | 0 | 17 | 25 | 34/133 | 2 | 3/128 |
| `sense_all` | 384 | 43 | 0.112 | 4 | 0 | 0 | 14 | 25 | 22/133 | 14 | 3/128 |
| `sense_known` | 384 | 46 | 0.120 | 4 | 0 | 0 | 17 | 25 | 34/133 | 2 | 3/128 |
| `credit_rank5` | 384 | 40 | 0.104 | 2 | 0 | 0 | 14 | 24 | 17/133 | 19 | 3/128 |

Picked: `known_off`.
