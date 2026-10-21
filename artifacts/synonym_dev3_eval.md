# dev3 set (hand-written 2026-10-21, split by golden source row; report-only)

Vocabulary problems: none. Split sizes: {'calib': 25, 'confirm': 20}.

| half | arm | correct | ANSWER | fail-open | spurious write | raw PII |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| calib | default (shipped) | 17/25 | 6/13 | 0 | 0 | 0 |
| calib | Datamuse context-gated, dev3-chosen (ships off: opens a unit-test trap) | 19/25 | 7/13 | 0 | 0 | 0 |
| calib | same, unknown words only (post-hoc, ships off) | 18/25 | 7/13 | 0 | 0 | 0 |
| confirm | default (shipped) | 11/20 | 4/12 | 0 | 0 | 0 |
| confirm | Datamuse context-gated, dev3-chosen (ships off: opens a unit-test trap) | 14/20 | 7/12 | 0 | 0 | 0 |
| confirm | same, unknown words only (post-hoc, ships off) | 13/20 | 6/12 | 0 | 0 | 0 |
