# Non-key coverage rule, one-shot confirm (`all`)

Rows: dev8 wordy (32) + dev7 + fresh + the 203-row robustness set (301); 684 swaps, seed 1109.

| arm | swaps | passed | pass rate | passage | translation | semantic | lexical | unsupported | ANSWER kept | lost | must-refuse opened |
| :--- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `shipped` | 684 | 74 | 0.108 | 0 | 0 | 0 | 45 | 29 | 66/125 | 0 | 9/157 |
| `all` | 684 | 32 | 0.047 | 0 | 0 | 0 | 32 | 0 | 63/125 | 3 | 9/157 |

dev8 wordy rows answered: shipped 20/32, `all` 17/32.
dev8 topic traps opened (16): shipped 5 ['d8-t02', 'd8-t03', 'd8-t05', 'd8-t08', 'd8-t12'], `all` 2 ['d8-t03', 'd8-t08'].
Attribute-trap opens (114 rows, v1-v3): shipped 0, `all` 0.
Answered rows lost: d8-06 (checkout), d8-29 (checkout), d8-30 (after)
Ships: **off**.
