# dev3 set (hand-written 2026-10-21, split by golden source row; report-only)

Vocabulary problems: none. Split sizes: {'calib': 25, 'confirm': 20}.

| half | arm | correct | ANSWER | fail-open | spurious write | raw PII |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| calib | default (shipped) | 16/25 | 6/13 | 0 | 0 | 0 |
| calib | Datamuse context-gated, dev3-chosen (ships off: opens a unit-test trap) | 18/25 | 7/13 | 0 | 0 | 0 |
| calib | same, unknown words only (post-hoc, ships off) | 17/25 | 7/13 | 0 | 0 | 0 |
| confirm | default (shipped) | 10/20 | 3/12 | 0 | 0 | 0 |
| confirm | Datamuse context-gated, dev3-chosen (ships off: opens a unit-test trap) | 13/20 | 6/12 | 0 | 0 | 0 |
| confirm | same, unknown words only (post-hoc, ships off) | 12/20 | 5/12 | 0 | 0 | 0 |
