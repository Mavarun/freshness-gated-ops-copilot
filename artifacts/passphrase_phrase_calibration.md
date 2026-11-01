# Function-word parts in compounds: calibrate (seeds 3307 / 3313 / 3319 / 3323 / 3301, 1,200 rows each; 3,025 SE train sentences, 1,920 SE train identifiers)

Pre-registered in `ops_copilot.passphrase_phrase_protocol`. `shipped` is the Nov 1 detector (shape guards on).

| arm | leak words std / glued / invented / cased / phrase (total) | over words | SE sentences flagged | SE ids flagged (new) | Oct 13 / queries / data ids | checks |
| --- | ---: | ---: | ---: | ---: | ---: | :---: |
| shipped | 7 / 7 / 0 / 10 / 1203 (1227) | 2494 | 28 | 166 (0) | 0 / 0 / 0 | yes |
| function_parts | 7 / 7 / 0 / 10 / 427 (451) | 2494 | 28 | 167 (1) | 0 / 0 / 0 | yes |

Checks: oct13_no_leak pass, repo_queries_unchanged pass, data_idents pass, se_sentences pass, se_identifiers pass, over_budget pass, no_more_leaks pass, gain pass

Passes: goes to the one-shot confirm.

Phrase probe by separator, leaked words shipped -> knob: dot 222 -> 10; hyphen 289 -> 17; space 398 -> 398; underscore 294 -> 2

Phrase leak causes with the knob: no_flag_ops 12, other 83, stop_inside 1, tail_trim 43

New SE train identifier flags: `WBC_ERR_DOMAIN_NOT_FOUND`
