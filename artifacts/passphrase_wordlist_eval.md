# Passphrases from the EFF large wordlist: shipped detector vs Oct 13

1,200 seeded rows per seed (4-6 EFF words, four separators, half Title-Case + number, five templates). All three seeds were spent by the Oct 29 protocol, so this is a regression report, not a fresh test.

| seed | rows leaking (Oct 13 -> shipped) | words leaked (Oct 13 -> shipped) | over-redacted template words |
| --- | ---: | ---: | ---: |
| 2910 | 46 -> 22 | 148 -> 114 of 5927 | 488 -> 510 |
| 2929 | 32 -> 12 | 93 -> 66 of 5978 | 503 -> 539 |
| 2931 | 41 -> 16 | 105 -> 76 of 5886 | 528 -> 549 |

Oct 13 probe words leaked: 0. Trace queries changed: 0. New identifier flags: 0.

Failures: none
