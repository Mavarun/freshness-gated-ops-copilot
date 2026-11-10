# Compound parts for the non-key rule, calibration (golden + dev2-dev6 + dev8)

320 rows (dev8's 16 topic traps count as must-refuse rows); the Nov 7 384 swaps (3 random corpus words per salient term, seed 1107). Mechanism columns count passed swaps by what supported the swapped-in word.

| arm | swaps | passed | pass rate | passage | translation | semantic | lexical | unsupported | ANSWER kept | lost | must-refuse opened |
| :--- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `shipped` | 384 | 42 | 0.109 | 0 | 0 | 0 | 17 | 25 | 54/165 | 0 | 8/144 |
| `all` | 384 | 14 | 0.036 | 0 | 0 | 0 | 14 | 0 | 49/165 | 5 | 5/144 |
| `all_hyphen` | 384 | 14 | 0.036 | 0 | 0 | 0 | 14 | 0 | 51/165 | 3 | 5/144 |
| `all_joined` | 384 | 14 | 0.036 | 0 | 0 | 0 | 14 | 0 | 51/165 | 3 | 5/144 |
| `corpus_hyphen` | 384 | 14 | 0.036 | 0 | 0 | 0 | 14 | 0 | 51/165 | 3 | 5/144 |

Calibration ANSWER rows lost per arm: `all` d5-22, d6-06, d8-06, d8-29, d8-30; `all_hyphen` d5-22, d6-06, d8-30; `all_joined` d5-22, d6-06, d8-30; `corpus_hyphen` d5-22, d6-06, d8-30

`all` is the Nov 9 reference and cannot be picked. No arm is eligible; confirm is not run.
