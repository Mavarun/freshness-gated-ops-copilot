# Non-key coverage rule, calibration (golden + dev2-dev6)

272 rows; the Nov 7 384 swaps (3 random corpus words per salient term, seed 1107). Mechanism columns count passed swaps by what supported the swapped-in word.

| arm | swaps | passed | pass rate | passage | translation | semantic | lexical | unsupported | ANSWER kept | lost | must-refuse opened |
| :--- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `shipped` | 384 | 42 | 0.109 | 0 | 0 | 0 | 17 | 25 | 34/133 | 0 | 3/128 |
| `all` | 384 | 14 | 0.036 | 0 | 0 | 0 | 14 | 0 | 32/133 | 2 | 3/128 |
| `corpus` | 384 | 14 | 0.036 | 0 | 0 | 0 | 14 | 0 | 32/133 | 2 | 3/128 |
| `idf_q25` | 384 | 34 | 0.089 | 0 | 0 | 0 | 17 | 17 | 34/133 | 0 | 3/128 |
| `idf_q50` | 384 | 42 | 0.109 | 0 | 0 | 0 | 17 | 25 | 34/133 | 0 | 3/128 |
| `cov_065` | 384 | 38 | 0.099 | 0 | 0 | 0 | 14 | 24 | 33/133 | 1 | 3/128 |

Calibration ANSWER rows lost per arm: `all` d5-22, d6-06; `corpus` d5-22, d6-06; `idf_q25` none; `idf_q50` none; `cov_065` d6-06

Picked: `all`.
