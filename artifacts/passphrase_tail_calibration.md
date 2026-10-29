# Passphrase tail / incoherence arms: calibration (seed 2910, 1200 EFF rows; 3,020 Stack Exchange train sentences)

Pre-registered in `ops_copilot.passphrase_tail_protocol`. Leaked = passphrase words (4+ letters) left in the redacted trace query. Over = template words redacted. SE flagged = train sentences with a flagged span (every flag is a false positive).

| arm | leak rows | leak words | over words | SE flagged | Oct 13 leaks | repo query changes | safe |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | :---: |
| trim/none | 46 | 148 | 488 | 17 | 0 | 0 | yes |
| trim/0.02 | 41 | 129 | 488 | 17 | 0 | 0 | yes |
| trim/0.05 | 39 | 120 | 488 | 20 | 0 | 0 | yes |
| trim/0.08 | 37 | 110 | 488 | 25 | 0 | 0 | yes |
| trim/0.10 | 36 | 105 | 488 | 28 | 0 | 0 | yes |
| trim/0.12 | 35 | 101 | 488 | 34 | 0 | 0 | no |
| trim/0.15 | 35 | 101 | 488 | 38 | 0 | 0 | no |
| keep/none | 25 | 125 | 510 | 17 | 0 | 0 | yes |
| keep/0.02 | 20 | 106 | 510 | 17 | 0 | 0 | yes |
| keep/0.05 | 18 | 97 | 510 | 20 | 0 | 0 | yes |
| keep/0.08 | 16 | 87 | 510 | 25 | 0 | 0 | yes |
| keep/0.10 | 15 | 82 | 510 | 28 | 0 | 0 | yes |
| keep/0.12 | 14 | 78 | 510 | 34 | 0 | 0 | no |
| keep/0.15 | 14 | 78 | 510 | 38 | 0 | 0 | no |

**Chosen:** `keep/0.10`

Leak causes, shipped detector: no_flag_ops 9, other 15, stop_inside 1, tail_trim 21

Leak causes, chosen arm: no_flag_ops 1, other 13, stop_inside 1

New Stack Exchange train flags (first few):

- `doesnt match Password Complexity requirements`
- `contains fully binary byte strings`
- `Credentials grant type deviates`
- `over completely different means`
