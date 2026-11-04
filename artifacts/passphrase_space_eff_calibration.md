# Space-joined function words (passphrase_space_eff): calibrate (seeds 3507 / 3513 / 3519 / 3523 / 3501 / 3527 / 3529, 1,200 rows each; 3,025 SE train sentences, 1,920 SE train identifiers)

Pre-registered in `ops_copilot.passphrase_space_eff_protocol`. `shipped` is the Nov 1 detector (function parts on, no space bridge).
Arms are `bridge list / max bridge words[ / rule]`.

| arm | leak words standard / attached / invented / cased / phrase / connective / offlist_phrase (total) | over words | SE sentences flagged | SE ids flagged (new) | Oct 13 / queries / data ids | checks |
| --- | ---: | ---: | ---: | ---: | ---: | :---: |
| shipped | 8 / 1 / 0 / 11 / 454 / 146 / 430 (1050) | 3542 | 28 | 167 (0) | 0 / 0 / 0 | baseline |
| prep/2/eff3 | 8 / 1 / 0 / 11 / 160 / 146 / 430 (756) | 3583 | 29 | 167 (0) | 0 / 0 / 0 | yes |
| prep/2/eff4 | 8 / 1 / 0 / 11 / 211 / 146 / 430 (807) | 3583 | 29 | 167 (0) | 0 / 0 / 0 | yes |
| func/2/eff3 | 8 / 1 / 0 / 11 / 70 / 146 / 430 (666) | 3599 | 30 | 167 (0) | 0 / 0 / 0 | yes |
| func/2/eff4 | 8 / 1 / 0 / 11 / 127 / 146 / 430 (723) | 3599 | 29 | 167 (0) | 0 / 0 / 0 | yes |

Checks `prep/2/eff3`: oct13_no_leak pass, repo_queries_unchanged pass, data_idents pass, se_sentences pass, se_identifiers pass, over_budget pass, no_more_leaks pass, gain pass
Checks `prep/2/eff4`: oct13_no_leak pass, repo_queries_unchanged pass, data_idents pass, se_sentences pass, se_identifiers pass, over_budget pass, no_more_leaks pass, gain pass
Checks `func/2/eff3`: oct13_no_leak pass, repo_queries_unchanged pass, data_idents pass, se_sentences pass, se_identifiers pass, over_budget pass, no_more_leaks pass, gain pass
Checks `func/2/eff4`: oct13_no_leak pass, repo_queries_unchanged pass, data_idents pass, se_sentences pass, se_identifiers pass, over_budget pass, no_more_leaks pass, gain pass

Pick: `func/2/eff3`. It goes to the one-shot confirm.

phrase probe by separator, leaked words shipped -> `prep/2/eff3`: dot 15 -> 15; hyphen 12 -> 12; space 417 -> 123; underscore 10 -> 10
phrase probe by separator, leaked words shipped -> `prep/2/eff4`: dot 15 -> 15; hyphen 12 -> 12; space 417 -> 174; underscore 10 -> 10
phrase probe by separator, leaked words shipped -> `func/2/eff3`: dot 15 -> 15; hyphen 12 -> 12; space 417 -> 33; underscore 10 -> 10
phrase probe by separator, leaked words shipped -> `func/2/eff4`: dot 15 -> 15; hyphen 12 -> 12; space 417 -> 90; underscore 10 -> 10
connective probe by separator, leaked words shipped -> `prep/2/eff3`: dot 55 -> 55; hyphen 50 -> 50; space 17 -> 17; underscore 24 -> 24
connective probe by separator, leaked words shipped -> `prep/2/eff4`: dot 55 -> 55; hyphen 50 -> 50; space 17 -> 17; underscore 24 -> 24
connective probe by separator, leaked words shipped -> `func/2/eff3`: dot 55 -> 55; hyphen 50 -> 50; space 17 -> 17; underscore 24 -> 24
connective probe by separator, leaked words shipped -> `func/2/eff4`: dot 55 -> 55; hyphen 50 -> 50; space 17 -> 17; underscore 24 -> 24
offlist_phrase probe by separator, leaked words shipped -> `prep/2/eff3`: dot 14 -> 14; hyphen 3 -> 3; space 392 -> 392; underscore 21 -> 21
offlist_phrase probe by separator, leaked words shipped -> `prep/2/eff4`: dot 14 -> 14; hyphen 3 -> 3; space 392 -> 392; underscore 21 -> 21
offlist_phrase probe by separator, leaked words shipped -> `func/2/eff3`: dot 14 -> 14; hyphen 3 -> 3; space 392 -> 392; underscore 21 -> 21
offlist_phrase probe by separator, leaked words shipped -> `func/2/eff4`: dot 14 -> 14; hyphen 3 -> 3; space 392 -> 392; underscore 21 -> 21
