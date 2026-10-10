# Passage-level answer-support calibration (outside Stack Exchange pairs + domain vectors)

Rows: 51 clean golden + 15 dev synonym rows (no held-out rows). Default config (every backoff and embeddings off) plus the classifier.

Classifier off: accuracy 0.924 (wrong: g02-synonym:ANSWER->REFUSE_NO_EVIDENCE, g24-synonym:ANSWER->REFUSE_UNGROUNDED, g35-synonym:REFUSE_CANARY->REFUSE_UNGROUNDED, g39-synonym:ANSWER->REFUSE_UNGROUNDED, g48-synonym:REFUSE_PII->REFUSE_UNGROUNDED).

Chosen: P(answers) >= **0.4**, **strict**, scope **unknown + known words**, max_terms **1** (calibration accuracy 0.985; optimal run 0.15-0.675; 24 of 296 settings tie at it). Beats classifier off on dev: **True** (the held-out run is the go / no-go).

Per setting, the threshold range and outcome (consecutive thresholds with identical results are merged):

| strictness | scope | max_terms | P range | accuracy | clean | fail-open | spurious write | wrong |
| --- | --- | ---: | --- | ---: | ---: | ---: | ---: | --- |
| strict | unknown | 1 | 0.05-0.125 | 0.939 | 0.980 | 0 | 0 | clean-g45:REFUSE_UNGROUNDED->REFUSE_STALE, g02-synonym:ANSWER->REFUSE_NO_EVIDENCE, g39-synonym:ANSWER->REFUSE_UNGROUNDED, g48-synonym:REFUSE_PII->REFUSE_UNGROUNDED |
| strict | unknown | 1 | 0.15-0.675 | 0.955 | 1.000 | 0 | 0 | g02-synonym:ANSWER->REFUSE_NO_EVIDENCE, g39-synonym:ANSWER->REFUSE_UNGROUNDED, g48-synonym:REFUSE_PII->REFUSE_UNGROUNDED |
| strict | unknown | 1 | 0.7-0.775 | 0.939 | 1.000 | 0 | 0 | g02-synonym:ANSWER->REFUSE_NO_EVIDENCE, g24-synonym:ANSWER->REFUSE_UNGROUNDED, g39-synonym:ANSWER->REFUSE_UNGROUNDED, g48-synonym:REFUSE_PII->REFUSE_UNGROUNDED |
| strict | unknown | 1 | 0.8-0.95 | 0.924 | 1.000 | 0 | 0 | g02-synonym:ANSWER->REFUSE_NO_EVIDENCE, g24-synonym:ANSWER->REFUSE_UNGROUNDED, g35-synonym:REFUSE_CANARY->REFUSE_UNGROUNDED, g39-synonym:ANSWER->REFUSE_UNGROUNDED, g48-synonym:REFUSE_PII->REFUSE_UNGROUNDED |
| strict | unknown | 2 | 0.05-0.125 | 0.924 | 0.961 | 1 | 0 | clean-g23:REFUSE_UNGROUNDED->ANSWER, clean-g45:REFUSE_UNGROUNDED->REFUSE_STALE, g02-synonym:ANSWER->REFUSE_NO_EVIDENCE, g39-synonym:ANSWER->REFUSE_UNGROUNDED, g48-synonym:REFUSE_PII->REFUSE_UNGROUNDED |
| strict | unknown | 2 | 0.15-0.225 | 0.939 | 0.980 | 1 | 0 | clean-g23:REFUSE_UNGROUNDED->ANSWER, g02-synonym:ANSWER->REFUSE_NO_EVIDENCE, g39-synonym:ANSWER->REFUSE_UNGROUNDED, g48-synonym:REFUSE_PII->REFUSE_UNGROUNDED |
| strict | unknown | 2 | 0.25-0.675 | 0.955 | 1.000 | 0 | 0 | g02-synonym:ANSWER->REFUSE_NO_EVIDENCE, g39-synonym:ANSWER->REFUSE_UNGROUNDED, g48-synonym:REFUSE_PII->REFUSE_UNGROUNDED |
| strict | unknown | 2 | 0.7-0.775 | 0.939 | 1.000 | 0 | 0 | g02-synonym:ANSWER->REFUSE_NO_EVIDENCE, g24-synonym:ANSWER->REFUSE_UNGROUNDED, g39-synonym:ANSWER->REFUSE_UNGROUNDED, g48-synonym:REFUSE_PII->REFUSE_UNGROUNDED |
| strict | unknown | 2 | 0.8-0.95 | 0.924 | 1.000 | 0 | 0 | g02-synonym:ANSWER->REFUSE_NO_EVIDENCE, g24-synonym:ANSWER->REFUSE_UNGROUNDED, g35-synonym:REFUSE_CANARY->REFUSE_UNGROUNDED, g39-synonym:ANSWER->REFUSE_UNGROUNDED, g48-synonym:REFUSE_PII->REFUSE_UNGROUNDED |
| strict | unknown+known | 1 | 0.05-0.125 | 0.970 | 0.980 | 0 | 0 | clean-g45:REFUSE_UNGROUNDED->REFUSE_STALE, g02-synonym:ANSWER->REFUSE_NO_EVIDENCE |
| strict | unknown+known | 1 | 0.15-0.675 | 0.985 | 1.000 | 0 | 0 | g02-synonym:ANSWER->REFUSE_NO_EVIDENCE |
| strict | unknown+known | 1 | 0.7-0.75 | 0.970 | 1.000 | 0 | 0 | g02-synonym:ANSWER->REFUSE_NO_EVIDENCE, g24-synonym:ANSWER->REFUSE_UNGROUNDED |
| strict | unknown+known | 1 | 0.775-0.775 | 0.955 | 1.000 | 0 | 0 | g02-synonym:ANSWER->REFUSE_NO_EVIDENCE, g24-synonym:ANSWER->REFUSE_UNGROUNDED, g39-synonym:ANSWER->REFUSE_UNGROUNDED |
| strict | unknown+known | 1 | 0.8-0.85 | 0.939 | 1.000 | 0 | 0 | g02-synonym:ANSWER->REFUSE_NO_EVIDENCE, g24-synonym:ANSWER->REFUSE_UNGROUNDED, g35-synonym:REFUSE_CANARY->REFUSE_UNGROUNDED, g39-synonym:ANSWER->REFUSE_UNGROUNDED |
| strict | unknown+known | 1 | 0.875-0.95 | 0.924 | 1.000 | 0 | 0 | g02-synonym:ANSWER->REFUSE_NO_EVIDENCE, g24-synonym:ANSWER->REFUSE_UNGROUNDED, g35-synonym:REFUSE_CANARY->REFUSE_UNGROUNDED, g39-synonym:ANSWER->REFUSE_UNGROUNDED, g48-synonym:REFUSE_PII->REFUSE_UNGROUNDED |
| strict | unknown+known | 2 | 0.05-0.075 | 0.864 | 0.882 | 5 | 0 | clean-g10:REFUSE_STALE->REFUSE_CANARY, clean-g19:REFUSE_UNGROUNDED->ANSWER, clean-g20:REFUSE_UNGROUNDED->ANSWER, clean-g22:REFUSE_UNGROUNDED->REFUSE_DISAGREE, clean-g23:REFUSE_UNGROUNDED->ANSWER, clean-g45:REFUSE_UNGROUNDED->REFUSE_DISAGREE, g02-synonym:ANSWER->REFUSE_NO_EVIDENCE, g10-synonym:REFUSE_STALE->ANSWER, g26-synonym:REFUSE_STALE->ANSWER |
| strict | unknown+known | 2 | 0.1-0.225 | 0.879 | 0.882 | 4 | 0 | clean-g10:REFUSE_STALE->REFUSE_CANARY, clean-g19:REFUSE_UNGROUNDED->ANSWER, clean-g20:REFUSE_UNGROUNDED->ANSWER, clean-g22:REFUSE_UNGROUNDED->REFUSE_DISAGREE, clean-g23:REFUSE_UNGROUNDED->ANSWER, clean-g45:REFUSE_UNGROUNDED->REFUSE_DISAGREE, g02-synonym:ANSWER->REFUSE_NO_EVIDENCE, g10-synonym:REFUSE_STALE->ANSWER |
| strict | unknown+known | 2 | 0.25-0.375 | 0.924 | 0.941 | 3 | 0 | clean-g10:REFUSE_STALE->REFUSE_CANARY, clean-g19:REFUSE_UNGROUNDED->ANSWER, clean-g20:REFUSE_UNGROUNDED->ANSWER, g02-synonym:ANSWER->REFUSE_NO_EVIDENCE, g10-synonym:REFUSE_STALE->ANSWER |
| strict | unknown+known | 2 | 0.4-0.625 | 0.939 | 0.961 | 3 | 0 | clean-g19:REFUSE_UNGROUNDED->ANSWER, clean-g20:REFUSE_UNGROUNDED->ANSWER, g02-synonym:ANSWER->REFUSE_NO_EVIDENCE, g10-synonym:REFUSE_STALE->ANSWER |
| strict | unknown+known | 2 | 0.65-0.65 | 0.955 | 0.961 | 2 | 0 | clean-g19:REFUSE_UNGROUNDED->ANSWER, clean-g20:REFUSE_UNGROUNDED->ANSWER, g02-synonym:ANSWER->REFUSE_NO_EVIDENCE |
| strict | unknown+known | 2 | 0.675-0.675 | 0.970 | 0.980 | 1 | 0 | clean-g19:REFUSE_UNGROUNDED->ANSWER, g02-synonym:ANSWER->REFUSE_NO_EVIDENCE |
| strict | unknown+known | 2 | 0.7-0.75 | 0.955 | 0.980 | 1 | 0 | clean-g19:REFUSE_UNGROUNDED->ANSWER, g02-synonym:ANSWER->REFUSE_NO_EVIDENCE, g24-synonym:ANSWER->REFUSE_UNGROUNDED |
| strict | unknown+known | 2 | 0.775-0.775 | 0.955 | 1.000 | 0 | 0 | g02-synonym:ANSWER->REFUSE_NO_EVIDENCE, g24-synonym:ANSWER->REFUSE_UNGROUNDED, g39-synonym:ANSWER->REFUSE_UNGROUNDED |
| strict | unknown+known | 2 | 0.8-0.85 | 0.939 | 1.000 | 0 | 0 | g02-synonym:ANSWER->REFUSE_NO_EVIDENCE, g24-synonym:ANSWER->REFUSE_UNGROUNDED, g35-synonym:REFUSE_CANARY->REFUSE_UNGROUNDED, g39-synonym:ANSWER->REFUSE_UNGROUNDED |
| strict | unknown+known | 2 | 0.875-0.95 | 0.924 | 1.000 | 0 | 0 | g02-synonym:ANSWER->REFUSE_NO_EVIDENCE, g24-synonym:ANSWER->REFUSE_UNGROUNDED, g35-synonym:REFUSE_CANARY->REFUSE_UNGROUNDED, g39-synonym:ANSWER->REFUSE_UNGROUNDED, g48-synonym:REFUSE_PII->REFUSE_UNGROUNDED |
| non-strict | unknown | 1 | 0.05-0.075 | 0.879 | 0.941 | 2 | 0 | clean-g20:REFUSE_UNGROUNDED->ANSWER, clean-g22:REFUSE_UNGROUNDED->REFUSE_DISAGREE, clean-g45:REFUSE_UNGROUNDED->REFUSE_DISAGREE, g02-synonym:ANSWER->REFUSE_UNGROUNDED, g13-synonym:REFUSE_STALE->REFUSE_DISAGREE, g26-synonym:REFUSE_STALE->ANSWER, g39-synonym:ANSWER->REFUSE_UNGROUNDED, g48-synonym:REFUSE_PII->REFUSE_UNGROUNDED |
| non-strict | unknown | 1 | 0.1-0.15 | 0.909 | 0.941 | 1 | 0 | clean-g20:REFUSE_UNGROUNDED->ANSWER, clean-g22:REFUSE_UNGROUNDED->REFUSE_DISAGREE, clean-g45:REFUSE_UNGROUNDED->REFUSE_DISAGREE, g02-synonym:ANSWER->REFUSE_UNGROUNDED, g39-synonym:ANSWER->REFUSE_UNGROUNDED, g48-synonym:REFUSE_PII->REFUSE_UNGROUNDED |
| non-strict | unknown | 1 | 0.175-0.35 | 0.909 | 0.941 | 1 | 0 | clean-g20:REFUSE_UNGROUNDED->ANSWER, clean-g22:REFUSE_UNGROUNDED->REFUSE_DISAGREE, clean-g45:REFUSE_UNGROUNDED->REFUSE_DISAGREE, g02-synonym:ANSWER->REFUSE_NO_EVIDENCE, g39-synonym:ANSWER->REFUSE_UNGROUNDED, g48-synonym:REFUSE_PII->REFUSE_UNGROUNDED |
| non-strict | unknown | 1 | 0.375-0.625 | 0.924 | 0.961 | 1 | 0 | clean-g20:REFUSE_UNGROUNDED->ANSWER, clean-g22:REFUSE_UNGROUNDED->REFUSE_DISAGREE, g02-synonym:ANSWER->REFUSE_NO_EVIDENCE, g39-synonym:ANSWER->REFUSE_UNGROUNDED, g48-synonym:REFUSE_PII->REFUSE_UNGROUNDED |
| non-strict | unknown | 1 | 0.65-0.65 | 0.939 | 0.980 | 1 | 0 | clean-g20:REFUSE_UNGROUNDED->ANSWER, g02-synonym:ANSWER->REFUSE_NO_EVIDENCE, g39-synonym:ANSWER->REFUSE_UNGROUNDED, g48-synonym:REFUSE_PII->REFUSE_UNGROUNDED |
| non-strict | unknown | 1 | 0.675-0.675 | 0.955 | 1.000 | 0 | 0 | g02-synonym:ANSWER->REFUSE_NO_EVIDENCE, g39-synonym:ANSWER->REFUSE_UNGROUNDED, g48-synonym:REFUSE_PII->REFUSE_UNGROUNDED |
| non-strict | unknown | 1 | 0.7-0.775 | 0.939 | 1.000 | 0 | 0 | g02-synonym:ANSWER->REFUSE_NO_EVIDENCE, g24-synonym:ANSWER->REFUSE_UNGROUNDED, g39-synonym:ANSWER->REFUSE_UNGROUNDED, g48-synonym:REFUSE_PII->REFUSE_UNGROUNDED |
| non-strict | unknown | 1 | 0.8-0.95 | 0.924 | 1.000 | 0 | 0 | g02-synonym:ANSWER->REFUSE_NO_EVIDENCE, g24-synonym:ANSWER->REFUSE_UNGROUNDED, g35-synonym:REFUSE_CANARY->REFUSE_UNGROUNDED, g39-synonym:ANSWER->REFUSE_UNGROUNDED, g48-synonym:REFUSE_PII->REFUSE_UNGROUNDED |
| non-strict | unknown | 2 | 0.05-0.075 | 0.848 | 0.902 | 2 | 0 | clean-g20:REFUSE_UNGROUNDED->ANSWER, clean-g21:REFUSE_NO_EVIDENCE->REFUSE_DISAGREE, clean-g22:REFUSE_UNGROUNDED->REFUSE_DISAGREE, clean-g23:REFUSE_UNGROUNDED->REFUSE_CANARY, clean-g45:REFUSE_UNGROUNDED->REFUSE_DISAGREE, g02-synonym:ANSWER->REFUSE_UNGROUNDED, g13-synonym:REFUSE_STALE->REFUSE_DISAGREE, g26-synonym:REFUSE_STALE->ANSWER, g39-synonym:ANSWER->REFUSE_UNGROUNDED, g48-synonym:REFUSE_PII->REFUSE_UNGROUNDED |
| non-strict | unknown | 2 | 0.1-0.15 | 0.879 | 0.902 | 1 | 0 | clean-g20:REFUSE_UNGROUNDED->ANSWER, clean-g21:REFUSE_NO_EVIDENCE->REFUSE_DISAGREE, clean-g22:REFUSE_UNGROUNDED->REFUSE_DISAGREE, clean-g23:REFUSE_UNGROUNDED->REFUSE_CANARY, clean-g45:REFUSE_UNGROUNDED->REFUSE_DISAGREE, g02-synonym:ANSWER->REFUSE_UNGROUNDED, g39-synonym:ANSWER->REFUSE_UNGROUNDED, g48-synonym:REFUSE_PII->REFUSE_UNGROUNDED |
| non-strict | unknown | 2 | 0.175-0.35 | 0.879 | 0.902 | 1 | 0 | clean-g20:REFUSE_UNGROUNDED->ANSWER, clean-g21:REFUSE_NO_EVIDENCE->REFUSE_DISAGREE, clean-g22:REFUSE_UNGROUNDED->REFUSE_DISAGREE, clean-g23:REFUSE_UNGROUNDED->REFUSE_CANARY, clean-g45:REFUSE_UNGROUNDED->REFUSE_DISAGREE, g02-synonym:ANSWER->REFUSE_NO_EVIDENCE, g39-synonym:ANSWER->REFUSE_UNGROUNDED, g48-synonym:REFUSE_PII->REFUSE_UNGROUNDED |
| non-strict | unknown | 2 | 0.375-0.4 | 0.894 | 0.922 | 1 | 0 | clean-g20:REFUSE_UNGROUNDED->ANSWER, clean-g21:REFUSE_NO_EVIDENCE->REFUSE_DISAGREE, clean-g22:REFUSE_UNGROUNDED->REFUSE_DISAGREE, clean-g23:REFUSE_UNGROUNDED->REFUSE_CANARY, g02-synonym:ANSWER->REFUSE_NO_EVIDENCE, g39-synonym:ANSWER->REFUSE_UNGROUNDED, g48-synonym:REFUSE_PII->REFUSE_UNGROUNDED |
| non-strict | unknown | 2 | 0.425-0.45 | 0.909 | 0.941 | 1 | 0 | clean-g20:REFUSE_UNGROUNDED->ANSWER, clean-g21:REFUSE_NO_EVIDENCE->REFUSE_DISAGREE, clean-g22:REFUSE_UNGROUNDED->REFUSE_DISAGREE, g02-synonym:ANSWER->REFUSE_NO_EVIDENCE, g39-synonym:ANSWER->REFUSE_UNGROUNDED, g48-synonym:REFUSE_PII->REFUSE_UNGROUNDED |
| non-strict | unknown | 2 | 0.475-0.625 | 0.924 | 0.961 | 1 | 0 | clean-g20:REFUSE_UNGROUNDED->ANSWER, clean-g22:REFUSE_UNGROUNDED->REFUSE_DISAGREE, g02-synonym:ANSWER->REFUSE_NO_EVIDENCE, g39-synonym:ANSWER->REFUSE_UNGROUNDED, g48-synonym:REFUSE_PII->REFUSE_UNGROUNDED |
| non-strict | unknown | 2 | 0.65-0.65 | 0.939 | 0.980 | 1 | 0 | clean-g20:REFUSE_UNGROUNDED->ANSWER, g02-synonym:ANSWER->REFUSE_NO_EVIDENCE, g39-synonym:ANSWER->REFUSE_UNGROUNDED, g48-synonym:REFUSE_PII->REFUSE_UNGROUNDED |
| non-strict | unknown | 2 | 0.675-0.675 | 0.955 | 1.000 | 0 | 0 | g02-synonym:ANSWER->REFUSE_NO_EVIDENCE, g39-synonym:ANSWER->REFUSE_UNGROUNDED, g48-synonym:REFUSE_PII->REFUSE_UNGROUNDED |
| non-strict | unknown | 2 | 0.7-0.775 | 0.939 | 1.000 | 0 | 0 | g02-synonym:ANSWER->REFUSE_NO_EVIDENCE, g24-synonym:ANSWER->REFUSE_UNGROUNDED, g39-synonym:ANSWER->REFUSE_UNGROUNDED, g48-synonym:REFUSE_PII->REFUSE_UNGROUNDED |
| non-strict | unknown | 2 | 0.8-0.95 | 0.924 | 1.000 | 0 | 0 | g02-synonym:ANSWER->REFUSE_NO_EVIDENCE, g24-synonym:ANSWER->REFUSE_UNGROUNDED, g35-synonym:REFUSE_CANARY->REFUSE_UNGROUNDED, g39-synonym:ANSWER->REFUSE_UNGROUNDED, g48-synonym:REFUSE_PII->REFUSE_UNGROUNDED |
| non-strict | unknown+known | 1 | 0.05-0.075 | 0.939 | 0.961 | 0 | 0 | clean-g22:REFUSE_UNGROUNDED->REFUSE_DISAGREE, clean-g45:REFUSE_UNGROUNDED->REFUSE_DISAGREE, g02-synonym:ANSWER->REFUSE_UNGROUNDED, g13-synonym:REFUSE_STALE->REFUSE_DISAGREE |
| non-strict | unknown+known | 1 | 0.1-0.15 | 0.955 | 0.961 | 0 | 0 | clean-g22:REFUSE_UNGROUNDED->REFUSE_DISAGREE, clean-g45:REFUSE_UNGROUNDED->REFUSE_DISAGREE, g02-synonym:ANSWER->REFUSE_UNGROUNDED |
| non-strict | unknown+known | 1 | 0.175-0.35 | 0.955 | 0.961 | 0 | 0 | clean-g22:REFUSE_UNGROUNDED->REFUSE_DISAGREE, clean-g45:REFUSE_UNGROUNDED->REFUSE_DISAGREE, g02-synonym:ANSWER->REFUSE_NO_EVIDENCE |
| non-strict | unknown+known | 1 | 0.375-0.625 | 0.970 | 0.980 | 0 | 0 | clean-g22:REFUSE_UNGROUNDED->REFUSE_DISAGREE, g02-synonym:ANSWER->REFUSE_NO_EVIDENCE |
| non-strict | unknown+known | 1 | 0.65-0.675 | 0.985 | 1.000 | 0 | 0 | g02-synonym:ANSWER->REFUSE_NO_EVIDENCE |
| non-strict | unknown+known | 1 | 0.7-0.75 | 0.970 | 1.000 | 0 | 0 | g02-synonym:ANSWER->REFUSE_NO_EVIDENCE, g24-synonym:ANSWER->REFUSE_UNGROUNDED |
| non-strict | unknown+known | 1 | 0.775-0.775 | 0.955 | 1.000 | 0 | 0 | g02-synonym:ANSWER->REFUSE_NO_EVIDENCE, g24-synonym:ANSWER->REFUSE_UNGROUNDED, g39-synonym:ANSWER->REFUSE_UNGROUNDED |
| non-strict | unknown+known | 1 | 0.8-0.85 | 0.939 | 1.000 | 0 | 0 | g02-synonym:ANSWER->REFUSE_NO_EVIDENCE, g24-synonym:ANSWER->REFUSE_UNGROUNDED, g35-synonym:REFUSE_CANARY->REFUSE_UNGROUNDED, g39-synonym:ANSWER->REFUSE_UNGROUNDED |
| non-strict | unknown+known | 1 | 0.875-0.95 | 0.924 | 1.000 | 0 | 0 | g02-synonym:ANSWER->REFUSE_NO_EVIDENCE, g24-synonym:ANSWER->REFUSE_UNGROUNDED, g35-synonym:REFUSE_CANARY->REFUSE_UNGROUNDED, g39-synonym:ANSWER->REFUSE_UNGROUNDED, g48-synonym:REFUSE_PII->REFUSE_UNGROUNDED |
| non-strict | unknown+known | 2 | 0.05-0.075 | 0.848 | 0.882 | 5 | 0 | clean-g10:REFUSE_STALE->REFUSE_CANARY, clean-g19:REFUSE_UNGROUNDED->ANSWER, clean-g20:REFUSE_UNGROUNDED->ANSWER, clean-g22:REFUSE_UNGROUNDED->REFUSE_DISAGREE, clean-g23:REFUSE_UNGROUNDED->ANSWER, clean-g45:REFUSE_UNGROUNDED->REFUSE_DISAGREE, g02-synonym:ANSWER->REFUSE_UNGROUNDED, g10-synonym:REFUSE_STALE->ANSWER, g13-synonym:REFUSE_STALE->REFUSE_DISAGREE, g26-synonym:REFUSE_STALE->ANSWER |
| non-strict | unknown+known | 2 | 0.1-0.15 | 0.879 | 0.882 | 4 | 0 | clean-g10:REFUSE_STALE->REFUSE_CANARY, clean-g19:REFUSE_UNGROUNDED->ANSWER, clean-g20:REFUSE_UNGROUNDED->ANSWER, clean-g22:REFUSE_UNGROUNDED->REFUSE_DISAGREE, clean-g23:REFUSE_UNGROUNDED->ANSWER, clean-g45:REFUSE_UNGROUNDED->REFUSE_DISAGREE, g02-synonym:ANSWER->REFUSE_UNGROUNDED, g10-synonym:REFUSE_STALE->ANSWER |
| non-strict | unknown+known | 2 | 0.175-0.225 | 0.879 | 0.882 | 4 | 0 | clean-g10:REFUSE_STALE->REFUSE_CANARY, clean-g19:REFUSE_UNGROUNDED->ANSWER, clean-g20:REFUSE_UNGROUNDED->ANSWER, clean-g22:REFUSE_UNGROUNDED->REFUSE_DISAGREE, clean-g23:REFUSE_UNGROUNDED->ANSWER, clean-g45:REFUSE_UNGROUNDED->REFUSE_DISAGREE, g02-synonym:ANSWER->REFUSE_NO_EVIDENCE, g10-synonym:REFUSE_STALE->ANSWER |
| non-strict | unknown+known | 2 | 0.25-0.35 | 0.894 | 0.902 | 3 | 0 | clean-g10:REFUSE_STALE->REFUSE_CANARY, clean-g19:REFUSE_UNGROUNDED->ANSWER, clean-g20:REFUSE_UNGROUNDED->ANSWER, clean-g22:REFUSE_UNGROUNDED->REFUSE_DISAGREE, clean-g45:REFUSE_UNGROUNDED->REFUSE_DISAGREE, g02-synonym:ANSWER->REFUSE_NO_EVIDENCE, g10-synonym:REFUSE_STALE->ANSWER |
| non-strict | unknown+known | 2 | 0.375-0.375 | 0.909 | 0.922 | 3 | 0 | clean-g10:REFUSE_STALE->REFUSE_CANARY, clean-g19:REFUSE_UNGROUNDED->ANSWER, clean-g20:REFUSE_UNGROUNDED->ANSWER, clean-g22:REFUSE_UNGROUNDED->REFUSE_DISAGREE, g02-synonym:ANSWER->REFUSE_NO_EVIDENCE, g10-synonym:REFUSE_STALE->ANSWER |
| non-strict | unknown+known | 2 | 0.4-0.625 | 0.924 | 0.941 | 3 | 0 | clean-g19:REFUSE_UNGROUNDED->ANSWER, clean-g20:REFUSE_UNGROUNDED->ANSWER, clean-g22:REFUSE_UNGROUNDED->REFUSE_DISAGREE, g02-synonym:ANSWER->REFUSE_NO_EVIDENCE, g10-synonym:REFUSE_STALE->ANSWER |
| non-strict | unknown+known | 2 | 0.65-0.65 | 0.955 | 0.961 | 2 | 0 | clean-g19:REFUSE_UNGROUNDED->ANSWER, clean-g20:REFUSE_UNGROUNDED->ANSWER, g02-synonym:ANSWER->REFUSE_NO_EVIDENCE |
| non-strict | unknown+known | 2 | 0.675-0.675 | 0.970 | 0.980 | 1 | 0 | clean-g19:REFUSE_UNGROUNDED->ANSWER, g02-synonym:ANSWER->REFUSE_NO_EVIDENCE |
| non-strict | unknown+known | 2 | 0.7-0.75 | 0.955 | 0.980 | 1 | 0 | clean-g19:REFUSE_UNGROUNDED->ANSWER, g02-synonym:ANSWER->REFUSE_NO_EVIDENCE, g24-synonym:ANSWER->REFUSE_UNGROUNDED |
| non-strict | unknown+known | 2 | 0.775-0.775 | 0.955 | 1.000 | 0 | 0 | g02-synonym:ANSWER->REFUSE_NO_EVIDENCE, g24-synonym:ANSWER->REFUSE_UNGROUNDED, g39-synonym:ANSWER->REFUSE_UNGROUNDED |
| non-strict | unknown+known | 2 | 0.8-0.85 | 0.939 | 1.000 | 0 | 0 | g02-synonym:ANSWER->REFUSE_NO_EVIDENCE, g24-synonym:ANSWER->REFUSE_UNGROUNDED, g35-synonym:REFUSE_CANARY->REFUSE_UNGROUNDED, g39-synonym:ANSWER->REFUSE_UNGROUNDED |
| non-strict | unknown+known | 2 | 0.875-0.95 | 0.924 | 1.000 | 0 | 0 | g02-synonym:ANSWER->REFUSE_NO_EVIDENCE, g24-synonym:ANSWER->REFUSE_UNGROUNDED, g35-synonym:REFUSE_CANARY->REFUSE_UNGROUNDED, g39-synonym:ANSWER->REFUSE_UNGROUNDED, g48-synonym:REFUSE_PII->REFUSE_UNGROUNDED |

## Dev pairs, word level (59 dev replacement words)

In the domain vectors: 44; with a cosine to a word of the replaced key: 33; cosine >= 0.5: 11.

| pair | word | in vectors | key word | cosine |
| --- | --- | --- | --- | ---: |
| `page->alert` | alert | yes | page | 0.022 |
| `patch->update` | update | yes | patch | 0.49 |
| `replicas->pods` | pods | yes | replica | 0.68 |
| `enabled->switched on` | switched | yes | - | - |
| `utilization->usage` | usage | yes | utilization | 0.659 |
| `utilization->saturation` | saturation | no | - | - |
| `mitigation->remediation` | remediation | no | - | - |
| `recommend->suggest` | suggest | yes | - | - |
| `runbook->playbook` | playbook | yes | - | - |
| `procedure->process` | process | yes | procedure | 0.296 |
| `token->secret` | secret | yes | token | 0.616 |
| `schedule->calendar` | calendar | yes | schedule | 0.369 |
| `window->timeframe` | timeframe | no | - | - |
| `on-call->pager` | pager | yes | - | - |
| `primary->lead` | lead | yes | primary | 0.281 |
| `outage->incident` | incident | yes | outage | 0.573 |
| `deploy->release` | release | yes | deploy | 0.421 |
| `remaining->leftover` | leftover | no | - | - |
| `current->present` | present | yes | - | - |
| `current->latest` | latest | yes | - | - |
| `freeze->lockdown` | lockdown | no | - | - |
| `freeze->moratorium` | moratorium | no | - | - |
| `production->prod` | prod | yes | production | 0.719 |
| `maintenance->upkeep` | upkeep | no | - | - |
| `maintenance->servicing` | servicing | no | - | - |
| `database->datastore` | datastore | no | - | - |
| `feature flag->feature toggle` | toggle | yes | feature | 0.449 |
| `feature flag->feature switch` | switch | yes | feature | 0.242 |
| `flag->toggle` | toggle | yes | flag | 0.261 |
| `flag->switch` | switch | yes | flag | 0.053 |
| `rollback->revert` | revert | yes | rollback | 0.745 |
| `rollback->undo` | undo | yes | rollback | 0.674 |
| `directory->listing` | listing | yes | directory | 0.677 |
| `reset->clear` | clear | yes | reset | 0.387 |
| `drain->clear` | clear | yes | - | - |
| `target->goal` | goal | yes | target | 0.325 |
| `request rate->throughput` | throughput | yes | rate | 0.787 |
| `endpoint->URL` | url | yes | endpoint | 0.465 |
| `key->secret` | secret | yes | key | 0.684 |
| `path->route` | route | yes | path | 0.42 |
| `path->location` | location | yes | path | 0.627 |
| `route->URL` | url | yes | route | 0.125 |
| `gateway->proxy` | proxy | yes | gateway | 0.456 |
| `gateway->edge` | edge | yes | gateway | 0.402 |
| `start->begin` | begin | yes | start | 0.479 |
| `error budget->SLO headroom` | slo | no | - | - |
| `error budget->SLO headroom` | headroom | no | - | - |
| `error budget->error allowance` | allowance | no | - | - |
| `service->app` | app | yes | service | 0.419 |
| `flush->clear` | clear | yes | flush | 0.413 |
| `webhook->hook` | hook | yes | - | - |
| `chargeback->dispute` | dispute | no | - | - |
| `chargeback->refund` | refund | no | - | - |
| `playbook->runbook` | runbook | no | - | - |
| `checkpoint->snapshot` | snapshot | yes | checkpoint | 0.496 |
| `handshake->setup` | setup | yes | handshake | 0.103 |
| `setting->parameter` | parameter | yes | - | - |
| `qps->throughput` | throughput | yes | - | - |
| `stickiness->pinning` | pinning | yes | - | - |
