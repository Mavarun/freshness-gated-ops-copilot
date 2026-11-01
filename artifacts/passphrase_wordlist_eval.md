# Passphrases from the EFF large wordlist: shipped detector vs Oct 13

1,200 seeded rows per seed (4-6 EFF words, four separators, half Title-Case + number, five templates). Every seed was spent by the Oct 29 or Oct 30 protocol, so this is a regression report, not a fresh test. `offlist-3053` is the Oct 30 control: the same rows built from WordNet nouns that are not on the EFF list.

| seed | rows leaking (Oct 13 -> Oct 29 -> shipped) | words leaked (Oct 13 -> Oct 29 -> shipped) | over-redacted template words |
| --- | ---: | ---: | ---: |
| 2910 | 46 -> 22 -> 2 | 148 -> 114 -> 6 of 5927 | 488 -> 510 -> 510 |
| 2929 | 32 -> 12 -> 1 | 93 -> 66 -> 5 of 5978 | 503 -> 539 -> 539 |
| 2931 | 41 -> 16 -> 6 | 105 -> 76 -> 24 of 5886 | 528 -> 549 -> 549 |
| 3010 | 46 -> 28 -> 9 | 155 -> 136 -> 37 of 5959 | 509 -> 533 -> 535 |
| 3037 | 46 -> 24 -> 4 | 175 -> 128 -> 16 of 5962 | 478 -> 507 -> 509 |
| offlist-3053 | 26 -> 12 -> 7 | 80 -> 63 -> 33 of 5990 | 492 -> 515 -> 515 |

Oct 31 rows: Bitwarden-style glued digit (`glued-*`, one digit 0-9 on one word) and invented words (`invented-*`, half strictly consonant-vowel, half closed syllables). All spent.

| rows | rows leaking (Oct 30 -> shipped) | words leaked (Oct 30 -> shipped) | over-redacted |
| --- | ---: | ---: | ---: |
| glued-3061 | 452 -> 3 | 1977 -> 3 of 5944 | 488 -> 540 |
| glued-3079 | 438 -> 3 | 1857 -> 7 of 5905 | 507 -> 581 |
| glued-3119 | 488 -> 4 | 2081 -> 16 of 5933 | 479 -> 549 |
| glued-3163 | 456 -> 4 | 1948 -> 10 of 5890 | 499 -> 558 |
| invented-3121 | 0 -> 0 | 0 -> 0 of 6016 | 506 -> 506 |
| invented-3167 | 0 -> 0 | 0 -> 0 of 5971 | 514 -> 514 |

Nov 1 rows (spent by the shape-guard protocol): the five probes on its calibration and confirm seeds, Oct 31 patterns vs shipped (shape guards `case` + `tld` on).

| rows | rows leaking (Oct 31 -> shipped) | words leaked (Oct 31 -> shipped) | over-redacted |
| --- | ---: | ---: | ---: |
| standard-3203 | 3 -> 3 | 15 -> 15 of 5980 | 506 -> 506 |
| attached-3209 | 4 -> 4 | 17 -> 17 of 5933 | 536 -> 536 |
| invented-3217 | 0 -> 0 | 0 -> 0 of 5988 | 475 -> 475 |
| cased-3221 | 2 -> 2 | 7 -> 7 of 5952 | 490 -> 490 |
| phrase-3229 | 370 -> 370 | 1252 -> 1252 of 4758 | 488 -> 488 |
| standard-3251 | 1 -> 1 | 1 -> 1 of 5904 | 515 -> 515 |
| attached-3253 | 9 -> 9 | 34 -> 34 of 5979 | 529 -> 529 |
| invented-3257 | 0 -> 0 | 0 -> 0 of 5966 | 480 -> 480 |
| cased-3259 | 2 -> 2 | 6 -> 6 of 5934 | 546 -> 546 |
| phrase-3271 | 368 -> 368 | 1273 -> 1273 of 4747 | 477 -> 477 |

Oct 13 probe words leaked: 0. Trace queries changed: 0. New identifier flags: 0.

Failures: none
