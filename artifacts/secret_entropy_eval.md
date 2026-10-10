# Random-token secret detector (no recognisable format)

Character trigram model trained on 19,838 committed outside words (counter-fitted table, Stack Exchange QA question words, Wiktionary computing senses, Stack Exchange tag names); 3,573 held-out words (salted hash) are calibration negatives together with identifier-style compounds of them. Score = bits per character of the worst `-_./:` piece of a token of 12+ characters.

## Calibration (dev families base62 / hex / lower_alnum, seed 7)

- lowest threshold with calibration FPR <= 0.005: **4.35**
- highest threshold that still catches every dev secret: **5.35**
- chosen (midpoint, rule fixed before the test run): **4.85** (committed default 4.85)
- 2,615 calibration negatives, 900 dev secrets

## Test: synthetic secrets (seed 2026, never real)

| family | in calibration | n | PR #16 patterns | detector | PR #16 + detector |
| --- | --- | ---: | ---: | ---: | ---: |
| base62 | yes | 200 | 0 | 200 | 200 |
| hex | yes | 200 | 0 | 200 | 200 |
| lower_alnum | yes | 200 | 0 | 200 | 200 |
| base64url | no | 200 | 0 | 198 | 198 |
| password_symbols | no | 200 | 0 | 200 | 200 |
| prefixed_pat | no | 200 | 0 | 200 | 200 |
| pronounceable | no | 200 | 0 | 76 | 76 |

Recall over all families: PR #16 0.000 -> now 0.910.

## Test: false positives on repo text the model never saw

| text | tokens | candidates (12+ chars) | already shape-redacted | flagged | flagged tokens |
| --- | ---: | ---: | ---: | ---: | --- |
| ops documents | 1452 | 98 | 0 | 0 | - |
| golden questions | 375 | 22 | 1 | 0 | - |
| perturbed questions | 1719 | 88 | 4 | 0 | - |
| write-intent eval | 245 | 44 | 0 | 0 | - |
| phrasal write eval | 182 | 31 | 0 | 0 | - |
| fresh synonym set | 190 | 10 | 0 | 0 | - |

False-positive rate on candidates: 0/293 (0.000).

## Planted documents (should be caught)

- canary documents: 16 candidates; flagged by the detector: `CNRY-CACHE1E6F`, `CNRY-MESH4D8C`, `CNRY-PAGER9K2B`, `CNRY-VAULT7F3A`
- PII documents: 16 candidates; flagged by the detector: -

Score examples (bits/char): `checkout_retry` 3.5, `payments-worker-heartbeat` 4.0, `redis.maxmemory-policy` 3.81, `q7xf2lpz9mkw3t` 7.01
