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
| phrase-3229 | 370 -> 140 | 1252 -> 399 of 4758 | 488 -> 488 |
| standard-3251 | 1 -> 1 | 1 -> 1 of 5904 | 515 -> 515 |
| attached-3253 | 9 -> 9 | 34 -> 34 of 5979 | 529 -> 529 |
| invented-3257 | 0 -> 0 | 0 -> 0 of 5966 | 480 -> 480 |
| cased-3259 | 2 -> 2 | 6 -> 6 of 5934 | 546 -> 546 |
| phrase-3271 | 368 -> 134 | 1273 -> 410 of 4747 | 477 -> 477 |

Nov 1 function-parts rows (spent by `passphrase_phrase_protocol`): shape-guard detector vs shipped (function-word parts on).

| rows | rows leaking (shape -> shipped) | words leaked (shape -> shipped) | over-redacted |
| --- | ---: | ---: | ---: |
| standard-3307 | 2 -> 2 | 7 -> 7 of 5948 | 521 -> 521 |
| attached-3313 | 3 -> 3 | 7 -> 7 of 5914 | 505 -> 505 |
| invented-3319 | 0 -> 0 | 0 -> 0 of 6022 | 483 -> 483 |
| cased-3323 | 2 -> 2 | 10 -> 10 of 5931 | 523 -> 523 |
| phrase-3301 | 356 -> 139 | 1203 -> 427 of 4761 | 462 -> 462 |
| standard-3329 | 4 -> 4 | 17 -> 17 of 5919 | 491 -> 491 |
| attached-3331 | 6 -> 6 | 22 -> 22 of 5912 | 527 -> 527 |
| invented-3343 | 0 -> 0 | 0 -> 0 of 5972 | 491 -> 491 |
| cased-3347 | 2 -> 2 | 10 -> 10 of 5905 | 528 -> 528 |
| phrase-3359 | 377 -> 147 | 1351 -> 487 of 4733 | 495 -> 495 |

Oct 13 probe words leaked: 0. Trace queries changed: 0. New identifier flags: 0.

Failures: none
