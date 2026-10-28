# What the shipped credited-word check vetoes (post-hoc, `credit_check_audit.py`)

Rows: 396 (calibration, dev7 confirm, traps v1-v3, fresh). Rows with a veto: 14. Effect vs the pre-change default: {'closed': 1, 'lost': 5, 'none': 8}.

Credited stop words: `only` 4, `not` 4, `before` 1, `no` 1, `already` 1, `other` 1, `two` 1, `one` 1.

| row | set | expected | check off -> on | effect | vetoed credit |
| :--- | :--- | :--- | :--- | :--- | :--- |
| at2-01 | traps_v2 | REFUSE_UNGROUNDED | ANSWER -> REFUSE_UNGROUNDED | closed | taste <- one |
| d3-02 | dev3 | ANSWER | ANSWER -> REFUSE_UNGROUNDED | lost | today <- only |
| d4-43 | dev4 | REFUSE_PII | REFUSE_PII -> REFUSE_UNGROUNDED | lost | identification <- only |
| d5-18 | dev5_tune | ANSWER | ANSWER -> REFUSE_UNGROUNDED | lost | gap <- only |
| d6-09 | dev6 | ANSWER | ANSWER -> REFUSE_UNGROUNDED | lost | available <- already |
| f13 | fresh | REFUSE_STALE | REFUSE_STALE -> REFUSE_UNGROUNDED | lost | ought <- not |
| at-12 | traps_v1 | REFUSE_UNGROUNDED | REFUSE_UNGROUNDED -> REFUSE_UNGROUNDED | none | flavour <- other |
| at-22 | traps_v1 | REFUSE_UNGROUNDED | REFUSE_UNGROUNDED -> REFUSE_UNGROUNDED | none | flavour <- two |
| at2-23 | traps_v2 | REFUSE_UNGROUNDED | REFUSE_UNGROUNDED -> REFUSE_UNGROUNDED | none | taste <- not |
| at2-40 | traps_v2 | REFUSE_UNGROUNDED | REFUSE_STALE -> REFUSE_STALE | none | salt <- not |
| d2-27 | dev2 | REFUSE_UNGROUNDED | REFUSE_UNGROUNDED -> REFUSE_UNGROUNDED | none | routine <- before |
| d4-08 | dev4 | ANSWER | REFUSE_UNGROUNDED -> REFUSE_UNGROUNDED | none | alive <- only |
| d4-26 | dev4 | REFUSE_STALE | REFUSE_UNGROUNDED -> REFUSE_UNGROUNDED | none | policy <- not |
| d4-29 | dev4 | REFUSE_STALE | REFUSE_UNGROUNDED -> REFUSE_UNGROUNDED | none | lifespan <- no |
