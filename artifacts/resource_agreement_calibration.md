# Resource-agreement backoff, calibration (golden + dev2-dev6 + dev8)

320 rows; the Nov 7 384 swaps (3 random corpus words per salient term, seed 1107). Mechanism columns count passed swaps by what supported the swapped-in word. New wrong evidence = arm answers citing other documents than the clean source question.

| arm | swaps | passed | pass rate | passage | translation | semantic | lexical | unsupported | ANSWER kept | gain | must-refuse opened | new wrong evidence |
| :--- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `shipped` | 384 | 42 | 0.109 | 0 | 0 | 0 | 17 | 25 | 54/165 | +0 | 8/144 | 0 |
| `agree2_known` | 384 | 45 | 0.117 | 0 | 0 | 0 | 20 | 25 | 54/165 | +0 | 8/144 | 0 |
| `agree3_known` | 384 | 43 | 0.112 | 0 | 0 | 0 | 18 | 25 | 54/165 | +0 | 8/144 | 0 |
| `agree2_lone` | 384 | 55 | 0.143 | 0 | 0 | 0 | 20 | 35 | 60/165 | +6 | 8/144 | 1 |
| `agree2_all` | 384 | 58 | 0.151 | 0 | 0 | 0 | 22 | 36 | 57/165 | +3 | 8/144 | 0 |
| `agree3_all` | 384 | 49 | 0.128 | 0 | 0 | 0 | 18 | 31 | 58/165 | +4 | 8/144 | 0 |

Rows whose decision changes per arm: `agree2_known` none; `agree3_known` none; `agree2_lone` d2-13 REFUSE_UNGROUNDED->ANSWER, d2-20 REFUSE_UNGROUNDED->REFUSE_PII, d2-21 REFUSE_UNGROUNDED->REFUSE_STALE, d4-06 REFUSE_UNGROUNDED->ANSWER, d4-19 REFUSE_UNGROUNDED->ANSWER, d4-22 REFUSE_UNGROUNDED->ANSWER, d5-04 REFUSE_UNGROUNDED->ANSWER, d5-42 REFUSE_UNGROUNDED->REFUSE_CANARY, d8-28 REFUSE_UNGROUNDED->ANSWER; `agree2_all` golden-14 REFUSE_NO_EVIDENCE->REFUSE_UNGROUNDED, golden-15 REFUSE_NO_EVIDENCE->REFUSE_UNGROUNDED, golden-21 REFUSE_NO_EVIDENCE->REFUSE_UNGROUNDED, golden-25 ANSWER->REFUSE_DISAGREE, d2-13 REFUSE_UNGROUNDED->ANSWER, d2-16 ANSWER->REFUSE_DISAGREE, d2-20 REFUSE_UNGROUNDED->ANSWER, d2-21 REFUSE_UNGROUNDED->REFUSE_STALE, d2-37 REFUSE_NO_EVIDENCE->REFUSE_UNGROUNDED, d3-07 REFUSE_UNGROUNDED->REFUSE_DISAGREE, d3-08 REFUSE_UNGROUNDED->REFUSE_DISAGREE, d3-39 REFUSE_UNGROUNDED->REFUSE_STALE, d4-06 REFUSE_UNGROUNDED->ANSWER, d4-19 REFUSE_UNGROUNDED->ANSWER, d4-21 ANSWER->REFUSE_DISAGREE, d4-22 REFUSE_UNGROUNDED->ANSWER, d5-04 REFUSE_UNGROUNDED->ANSWER, d5-21 ANSWER->REFUSE_DISAGREE, d5-42 REFUSE_UNGROUNDED->REFUSE_CANARY, d6-17 REFUSE_UNGROUNDED->REFUSE_DISAGREE, d6-42 REFUSE_NO_EVIDENCE->REFUSE_UNGROUNDED, d8-01 ANSWER->REFUSE_DISAGREE, d8-14 REFUSE_DISAGREE->ANSWER, d8-28 REFUSE_UNGROUNDED->ANSWER; `agree3_all` golden-15 REFUSE_NO_EVIDENCE->REFUSE_UNGROUNDED, d2-13 REFUSE_UNGROUNDED->ANSWER, d2-20 REFUSE_UNGROUNDED->ANSWER, d2-21 REFUSE_UNGROUNDED->REFUSE_STALE, d4-22 REFUSE_UNGROUNDED->ANSWER, d5-42 REFUSE_UNGROUNDED->REFUSE_CANARY, d8-28 REFUSE_UNGROUNDED->ANSWER

No arm is eligible; the confirm is not run and dev10 stays unseen.
