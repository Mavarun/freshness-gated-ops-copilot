# Fresh general-English synonym set (hand-written, separate from the 203 rows)

26 rows in `data/eval/synonym_fresh.jsonl`: golden queries with one or two general-English swaps, golden labels kept. Written by the backoff's author after it was calibrated, so this is a check of what the resource is for, not a blind benchmark. Vocabulary overlap with the perturbation split / synonym map: none.

| config | accuracy | ANSWER rows correct | fail-open | spurious write | raw PII |
| --- | ---: | ---: | ---: | ---: | ---: |
| default (word-vector backoff off; = PR #14) | 7/26 (0.269) | 0/11 | 0 | 0 | 0 |
| + word-vector backoff (calibrated) | 10/26 (0.385) | 1/11 | 0 | 0 | 0 |
| + word-vector backoff, unknown words only | 10/26 (0.385) | 1/11 | 0 | 0 | 0 |
| + corpus PPMI backoff (PR #11, for comparison) | 7/26 (0.269) | 0/11 | 0 | 0 | 0 |
| + Stack Exchange tag synonyms (dev-chosen) | 7/26 (0.269) | 0/11 | 0 | 0 | 0 |
| + Wiktionary computing senses (dev-chosen) | 7/26 (0.269) | 0/11 | 0 | 0 | 0 |
| + tag synonyms + Wiktionary + word vectors | 10/26 (0.385) | 1/11 | 0 | 0 | 0 |
| + answer-support model (dev-chosen) | 8/26 (0.308) | 1/11 | 0 | 0 | 0 |
| + answer-support model + word vectors | 11/26 (0.423) | 2/11 | 0 | 0 | 0 |
| + passage classifier (dev-chosen) | 18/26 (0.692) | 5/11 | 0 | 0 | 0 |
| + passage classifier + word vectors | 19/26 (0.731) | 5/11 | 0 | 0 | 0 |

| row | swap | expected | default (word-vector backoff off; = PR #14) | + word-vector backoff (calibrated) | + word-vector backoff, unknown words only | + corpus PPMI backoff (PR #11, for comparison) | + Stack Exchange tag synonyms (dev-chosen) | + Wiktionary computing senses (dev-chosen) | + tag synonyms + Wiktionary + word vectors | + answer-support model (dev-chosen) | + answer-support model + word vectors | + passage classifier (dev-chosen) | + passage classifier + word vectors |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| f01 | current -> at this moment | ANSWER | REFUSE_UNGROUNDED | REFUSE_UNGROUNDED | REFUSE_UNGROUNDED | REFUSE_UNGROUNDED | REFUSE_UNGROUNDED | REFUSE_UNGROUNDED | REFUSE_UNGROUNDED | REFUSE_UNGROUNDED | REFUSE_UNGROUNDED | **ok** | **ok** |
| f02 | enabled -> active | ANSWER | REFUSE_UNGROUNDED | REFUSE_UNGROUNDED | REFUSE_UNGROUNDED | REFUSE_UNGROUNDED | REFUSE_UNGROUNDED | REFUSE_UNGROUNDED | REFUSE_UNGROUNDED | REFUSE_UNGROUNDED | REFUSE_UNGROUNDED | REFUSE_UNGROUNDED | REFUSE_UNGROUNDED |
| f03 | primary -> principal | ANSWER | REFUSE_UNGROUNDED | REFUSE_UNGROUNDED | REFUSE_UNGROUNDED | REFUSE_UNGROUNDED | REFUSE_UNGROUNDED | REFUSE_UNGROUNDED | REFUSE_UNGROUNDED | **ok** | **ok** | REFUSE_UNGROUNDED | REFUSE_UNGROUNDED |
| f04 | running -> operating | ANSWER | REFUSE_UNGROUNDED | REFUSE_UNGROUNDED | REFUSE_UNGROUNDED | REFUSE_UNGROUNDED | REFUSE_UNGROUNDED | REFUSE_UNGROUNDED | REFUSE_UNGROUNDED | REFUSE_UNGROUNDED | REFUSE_UNGROUNDED | REFUSE_UNGROUNDED | REFUSE_UNGROUNDED |
| f05 | remaining -> residual | ANSWER | REFUSE_UNGROUNDED | REFUSE_UNGROUNDED | REFUSE_UNGROUNDED | REFUSE_UNGROUNDED | REFUSE_UNGROUNDED | REFUSE_UNGROUNDED | REFUSE_UNGROUNDED | REFUSE_UNGROUNDED | REFUSE_UNGROUNDED | **ok** | **ok** |
| f06 | mitigation -> remedy, recommend -> propose | ANSWER | REFUSE_UNGROUNDED | REFUSE_UNGROUNDED | REFUSE_UNGROUNDED | REFUSE_UNGROUNDED | REFUSE_UNGROUNDED | REFUSE_UNGROUNDED | REFUSE_UNGROUNDED | REFUSE_UNGROUNDED | REFUSE_UNGROUNDED | REFUSE_UNGROUNDED | REFUSE_UNGROUNDED |
| f07 | utilization -> consumption | ANSWER | REFUSE_UNGROUNDED | REFUSE_UNGROUNDED | REFUSE_UNGROUNDED | REFUSE_UNGROUNDED | REFUSE_UNGROUNDED | REFUSE_UNGROUNDED | REFUSE_UNGROUNDED | REFUSE_UNGROUNDED | REFUSE_UNGROUNDED | REFUSE_UNGROUNDED | REFUSE_UNGROUNDED |
| f08 | status -> condition | ANSWER | REFUSE_UNGROUNDED | REFUSE_UNGROUNDED | REFUSE_UNGROUNDED | REFUSE_UNGROUNDED | REFUSE_UNGROUNDED | REFUSE_UNGROUNDED | REFUSE_UNGROUNDED | REFUSE_UNGROUNDED | REFUSE_UNGROUNDED | REFUSE_UNGROUNDED | REFUSE_UNGROUNDED |
| f09 | window -> slot | ANSWER | REFUSE_UNGROUNDED | REFUSE_UNGROUNDED | REFUSE_UNGROUNDED | REFUSE_UNGROUNDED | REFUSE_UNGROUNDED | REFUSE_UNGROUNDED | REFUSE_UNGROUNDED | REFUSE_UNGROUNDED | REFUSE_UNGROUNDED | **ok** | **ok** |
| f10 | start -> commence | ANSWER | REFUSE_UNGROUNDED | **ok** | **ok** | REFUSE_UNGROUNDED | REFUSE_UNGROUNDED | REFUSE_UNGROUNDED | **ok** | REFUSE_UNGROUNDED | **ok** | **ok** | **ok** |
| f11 | schedule -> agenda | ANSWER | REFUSE_UNGROUNDED | REFUSE_UNGROUNDED | REFUSE_UNGROUNDED | REFUSE_UNGROUNDED | REFUSE_UNGROUNDED | REFUSE_UNGROUNDED | REFUSE_UNGROUNDED | REFUSE_UNGROUNDED | REFUSE_UNGROUNDED | **ok** | **ok** |
| f12 | run -> carry out | REFUSE_STALE | REFUSE_UNGROUNDED | REFUSE_UNGROUNDED | REFUSE_UNGROUNDED | REFUSE_UNGROUNDED | REFUSE_UNGROUNDED | REFUSE_UNGROUNDED | REFUSE_UNGROUNDED | REFUSE_UNGROUNDED | REFUSE_UNGROUNDED | REFUSE_UNGROUNDED | REFUSE_UNGROUNDED |
| f13 | should -> ought | REFUSE_STALE | REFUSE_UNGROUNDED | REFUSE_UNGROUNDED | REFUSE_UNGROUNDED | REFUSE_UNGROUNDED | REFUSE_UNGROUNDED | REFUSE_UNGROUNDED | REFUSE_UNGROUNDED | REFUSE_UNGROUNDED | REFUSE_UNGROUNDED | **ok** | **ok** |
| f14 | target -> aim | REFUSE_STALE | REFUSE_UNGROUNDED | **ok** | **ok** | REFUSE_UNGROUNDED | REFUSE_UNGROUNDED | REFUSE_UNGROUNDED | **ok** | REFUSE_UNGROUNDED | **ok** | REFUSE_UNGROUNDED | **ok** |
| f15 | drain -> empty | REFUSE_STALE | REFUSE_UNGROUNDED | REFUSE_UNGROUNDED | REFUSE_UNGROUNDED | REFUSE_UNGROUNDED | REFUSE_UNGROUNDED | REFUSE_UNGROUNDED | REFUSE_UNGROUNDED | REFUSE_UNGROUNDED | REFUSE_UNGROUNDED | **ok** | **ok** |
| f16 | payroll -> wage | REFUSE_NO_EVIDENCE | **ok** | **ok** | **ok** | **ok** | **ok** | **ok** | **ok** | **ok** | **ok** | **ok** | **ok** |
| f17 | password -> passcode | REFUSE_NO_EVIDENCE | **ok** | **ok** | **ok** | **ok** | **ok** | **ok** | **ok** | **ok** | **ok** | **ok** | **ok** |
| f18 | procedure -> method | REFUSE_UNGROUNDED | **ok** | **ok** | **ok** | **ok** | **ok** | **ok** | **ok** | **ok** | **ok** | **ok** | **ok** |
| f19 | playbook -> handbook | REFUSE_UNGROUNDED | **ok** | **ok** | **ok** | **ok** | **ok** | **ok** | **ok** | **ok** | **ok** | **ok** | **ok** |
| f20 | configured -> defined | REFUSE_UNGROUNDED | **ok** | **ok** | **ok** | **ok** | **ok** | **ok** | **ok** | **ok** | **ok** | **ok** | **ok** |
| f21 | path -> pathway | REFUSE_CANARY | REFUSE_UNGROUNDED | **ok** | **ok** | REFUSE_UNGROUNDED | REFUSE_UNGROUNDED | REFUSE_UNGROUNDED | **ok** | REFUSE_UNGROUNDED | **ok** | **ok** | **ok** |
| f22 | id -> identifier | REFUSE_PII | REFUSE_UNGROUNDED | REFUSE_UNGROUNDED | REFUSE_UNGROUNDED | REFUSE_UNGROUNDED | REFUSE_UNGROUNDED | REFUSE_UNGROUNDED | REFUSE_UNGROUNDED | REFUSE_UNGROUNDED | REFUSE_UNGROUNDED | **ok** | **ok** |
| f23 | now -> immediately | PROPOSE_WRITE | **ok** | **ok** | **ok** | **ok** | **ok** | **ok** | **ok** | **ok** | **ok** | **ok** | **ok** |
| f24 | can -> could | PROPOSE_WRITE | **ok** | **ok** | **ok** | **ok** | **ok** | **ok** | **ok** | **ok** | **ok** | **ok** | **ok** |
| f25 | budget -> allotment | REFUSE_DISAGREE | REFUSE_UNGROUNDED | REFUSE_UNGROUNDED | REFUSE_UNGROUNDED | REFUSE_UNGROUNDED | REFUSE_UNGROUNDED | REFUSE_UNGROUNDED | REFUSE_UNGROUNDED | REFUSE_UNGROUNDED | REFUSE_UNGROUNDED | **ok** | **ok** |
| f26 | cadence -> periodicity | REFUSE_DISAGREE | REFUSE_UNGROUNDED | REFUSE_UNGROUNDED | REFUSE_UNGROUNDED | REFUSE_UNGROUNDED | REFUSE_UNGROUNDED | REFUSE_UNGROUNDED | REFUSE_UNGROUNDED | REFUSE_UNGROUNDED | REFUSE_UNGROUNDED | **ok** | **ok** |
