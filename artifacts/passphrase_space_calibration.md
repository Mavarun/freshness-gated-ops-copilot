# Space-joined function words: calibrate (seeds 3407 / 3413 / 3419 / 3423 / 3401 / 3427, 1,200 rows each; 3,025 SE train sentences, 1,920 SE train identifiers)

Pre-registered in `ops_copilot.passphrase_space_protocol`. `shipped` is the Nov 1 detector (function parts on, no space bridge).
Arms are `bridge list / max bridge words`.

| arm | leak words std / glued / invented / cased / phrase / connective (total) | over words | SE sentences flagged | SE ids flagged (new) | Oct 13 / queries / data ids | checks |
| --- | ---: | ---: | ---: | ---: | ---: | :---: |
| shipped | 2 / 4 / 0 / 16 / 468 / 135 (625) | 3077 | 28 | 167 (0) | 0 / 0 / 0 | baseline |
| prep/1 | 2 / 4 / 0 / 16 / 207 / 135 (364) | 3310 | 56 | 167 (0) | 0 / 0 / 0 | no: se_sentences |
| prep/2 | 2 / 4 / 0 / 16 / 207 / 135 (364) | 3310 | 64 | 167 (0) | 0 / 0 / 0 | no: se_sentences |
| func/2 | 2 / 4 / 0 / 16 / 94 / 135 (251) | 3360 | 75 | 167 (0) | 0 / 0 / 0 | no: se_sentences |
| stop/2 | 2 / 4 / 0 / 12 / 94 / 132 (244) | 3362 | 84 | 167 (0) | 0 / 0 / 0 | no: se_sentences |

Checks `prep/1`: oct13_no_leak pass, repo_queries_unchanged pass, data_idents pass, se_sentences FAIL, se_identifiers pass, over_budget pass, no_more_leaks pass, gain pass
Checks `prep/2`: oct13_no_leak pass, repo_queries_unchanged pass, data_idents pass, se_sentences FAIL, se_identifiers pass, over_budget pass, no_more_leaks pass, gain pass
Checks `func/2`: oct13_no_leak pass, repo_queries_unchanged pass, data_idents pass, se_sentences FAIL, se_identifiers pass, over_budget pass, no_more_leaks pass, gain pass
Checks `stop/2`: oct13_no_leak pass, repo_queries_unchanged pass, data_idents pass, se_sentences FAIL, se_identifiers pass, over_budget pass, no_more_leaks pass, gain pass

No arm is safe with a gain: the knob stays off and the confirm seeds stay unspent.

phrase probe by separator, leaked words shipped -> `prep/1`: dot 7 -> 7; hyphen 14 -> 14; space 437 -> 176; underscore 10 -> 10
phrase probe by separator, leaked words shipped -> `prep/2`: dot 7 -> 7; hyphen 14 -> 14; space 437 -> 176; underscore 10 -> 10
phrase probe by separator, leaked words shipped -> `func/2`: dot 7 -> 7; hyphen 14 -> 14; space 437 -> 63; underscore 10 -> 10
phrase probe by separator, leaked words shipped -> `stop/2`: dot 7 -> 7; hyphen 14 -> 14; space 437 -> 63; underscore 10 -> 10
connective probe by separator, leaked words shipped -> `prep/1`: dot 31 -> 31; hyphen 35 -> 35; space 28 -> 28; underscore 41 -> 41
connective probe by separator, leaked words shipped -> `prep/2`: dot 31 -> 31; hyphen 35 -> 35; space 28 -> 28; underscore 41 -> 41
connective probe by separator, leaked words shipped -> `func/2`: dot 31 -> 31; hyphen 35 -> 35; space 28 -> 28; underscore 41 -> 41
connective probe by separator, leaked words shipped -> `stop/2`: dot 31 -> 31; hyphen 35 -> 35; space 28 -> 25; underscore 41 -> 41
