# Duplicate-paraphrase backoff, calibration (golden + dev2-dev6 + dev8)

320 rows; the swap null control's 384 swaps (3 random corpus words per salient term, seed 1107). Mechanism columns count passed swaps by what supported the swapped-in word. New wrong evidence = arm answers citing other documents than the clean source question.

| arm | swaps | passed | pass rate | passage | translation | semantic | lexical | unsupported | ANSWER kept | gain | must-refuse opened | new wrong evidence |
| :--- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `shipped` | 384 | 14 | 0.036 | 0 | 0 | 0 | 14 | 0 | 52/165 | +0 | 5/144 | 0 |
| `strict_known` | 384 | 18 | 0.047 | 0 | 0 | 0 | 18 | 0 | 52/165 | +0 | 5/144 | 0 |
| `strict_lone` | 384 | 18 | 0.047 | 0 | 0 | 0 | 18 | 0 | 53/165 | +1 | 5/144 | 0 |
| `strict_all` | 384 | 18 | 0.047 | 0 | 0 | 0 | 18 | 0 | 53/165 | +1 | 5/144 | 0 |
| `loose_lone` | 384 | 21 | 0.055 | 0 | 0 | 0 | 21 | 0 | 55/165 | +3 | 5/144 | 0 |
| `loose_all` | 384 | 24 | 0.062 | 0 | 0 | 0 | 24 | 0 | 54/165 | +2 | 5/144 | 0 |

Rows whose decision changes per arm: `strict_known` d8-t06 REFUSE_UNGROUNDED->REFUSE_STALE; `strict_lone` d6-23 REFUSE_UNGROUNDED->ANSWER, d8-t06 REFUSE_UNGROUNDED->REFUSE_STALE; `strict_all` golden-14 REFUSE_NO_EVIDENCE->REFUSE_UNGROUNDED, golden-21 REFUSE_NO_EVIDENCE->REFUSE_UNGROUNDED, d2-37 REFUSE_NO_EVIDENCE->REFUSE_UNGROUNDED, d3-17 REFUSE_UNGROUNDED->REFUSE_DISAGREE, d6-23 REFUSE_UNGROUNDED->ANSWER, d6-32 REFUSE_UNGROUNDED->REFUSE_STALE, d8-30 REFUSE_UNGROUNDED->REFUSE_DISAGREE, d8-t06 REFUSE_UNGROUNDED->REFUSE_STALE; `loose_lone` d3-01 REFUSE_UNGROUNDED->REFUSE_DISAGREE, d3-21 REFUSE_UNGROUNDED->ANSWER, d3-27 REFUSE_UNGROUNDED->REFUSE_STALE, d6-23 REFUSE_UNGROUNDED->ANSWER, d8-32 REFUSE_UNGROUNDED->ANSWER, d8-t06 REFUSE_UNGROUNDED->REFUSE_STALE; `loose_all` golden-14 REFUSE_NO_EVIDENCE->REFUSE_UNGROUNDED, golden-16 REFUSE_NO_EVIDENCE->REFUSE_UNGROUNDED, golden-21 REFUSE_NO_EVIDENCE->REFUSE_UNGROUNDED, d2-37 REFUSE_NO_EVIDENCE->REFUSE_UNGROUNDED, d3-01 REFUSE_UNGROUNDED->REFUSE_DISAGREE, d3-07 REFUSE_UNGROUNDED->REFUSE_STALE, d3-15 REFUSE_UNGROUNDED->REFUSE_DISAGREE, d3-17 REFUSE_UNGROUNDED->REFUSE_DISAGREE, d3-21 REFUSE_UNGROUNDED->ANSWER, d3-27 REFUSE_UNGROUNDED->REFUSE_STALE, d4-07 REFUSE_UNGROUNDED->REFUSE_STALE, d6-06 REFUSE_UNGROUNDED->REFUSE_STALE, d6-23 REFUSE_UNGROUNDED->ANSWER, d6-32 REFUSE_UNGROUNDED->REFUSE_STALE, d8-03 ANSWER->REFUSE_DISAGREE, d8-30 REFUSE_UNGROUNDED->REFUSE_DISAGREE, d8-32 REFUSE_UNGROUNDED->ANSWER, d8-t06 REFUSE_UNGROUNDED->REFUSE_STALE

No arm is eligible; the confirm is not run and dev10 stays unseen.
