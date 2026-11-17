# Citation-aware non-key protocol, one-shot confirm (`all_hyphen`)

Rows: dev9 wordy (32) + dev7 + fresh + the 203-row robustness set (301); 591 swaps, seed 1110.

| arm | swaps | passed | pass rate | passage | translation | semantic | lexical | unsupported | ANSWER kept | decision lost | fixed (wrong evidence) | budget lost | new wrong evidence | must-refuse opened |
| :--- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `shipped` | 591 | 83 | 0.140 | 0 | 0 | 0 | 44 | 39 | 59/125 | 0 | 0 | 0 | 0 | 9/157 |
| `all_hyphen` | 591 | 31 | 0.052 | 0 | 0 | 0 | 31 | 0 | 58/125 | 1 | 0 | 1 | 0 | 9/157 |
| `all` | 591 | 31 | 0.052 | 0 | 0 | 0 | 31 | 0 | 57/125 | 2 | 0 | 2 | 0 | 9/157 |

- `all_hyphen`: lost d9-15; fixed none; unlabelled lost none; new wrong evidence none
- `all`: lost d9-14, d9-15; fixed none; unlabelled lost none; new wrong evidence none

dev9 wordy rows answered: `shipped` 13/32, `all_hyphen` 12/32, `all` 11/32.
dev9 topic traps opened (16): `shipped` 1 [d9-t02], `all_hyphen` 0 [none], `all` 0 [none].
Attribute-trap opens (114 rows, v1-v3): `shipped` 0, `all_hyphen` 0, `all` 0.
Held-out ANSWER rows answered (9, report-only): `shipped` 0, `all_hyphen` 0, `all` 0.
Ships: **on**.
