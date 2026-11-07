# Swap null control, one-shot confirm (`known_off`)

Rows: dev7 + fresh + the 203-row robustness set (269); 459 swaps, seed 2611.

| arm | swaps | passed | pass rate | passage | translation | semantic | lexical | unsupported | ANSWER kept | lost | must-refuse opened |
| :--- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `shipped` | 459 | 187 | 0.407 | 129 | 0 | 0 | 40 | 18 | 48/93 | 0 | 9/157 |
| `known_off` | 459 | 69 | 0.150 | 0 | 0 | 0 | 37 | 32 | 46/93 | 2 | 9/157 |

Attribute-trap opens (114 rows, v1-v3): shipped 0, `known_off` 0.
Ships: **on**.
