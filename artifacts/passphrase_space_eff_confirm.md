# Space-joined function words (passphrase_space_eff): confirm (seeds 3533 / 3539 / 3549 / 3557 / 3561 / 3563 / 3567, 1,200 rows each; 306 SE test sentences, 147 SE test identifiers)

Pre-registered in `ops_copilot.passphrase_space_eff_protocol`. `shipped` is the Nov 1 detector (function parts on, no space bridge).
Arms are `bridge list / max bridge words[ / rule]`.

| arm | leak words standard / attached / invented / cased / phrase / connective / offlist_phrase (total) | over words | SE sentences flagged | SE ids flagged (new) | Oct 13 / queries / data ids | checks |
| --- | ---: | ---: | ---: | ---: | ---: | :---: |
| shipped | 28 / 16 / 0 / 5 / 420 / 173 / 457 (1099) | 3654 | 0 | 21 (0) | 0 / 0 / 0 | baseline |
| func/2/eff3 | 28 / 16 / 0 / 5 / 49 / 173 / 457 (728) | 3716 | 2 | 21 (0) | 0 / 0 / 0 | no: se_sentences |

Checks `func/2/eff3`: oct13_no_leak pass, repo_queries_unchanged pass, data_idents pass, se_sentences FAIL, se_identifiers pass, over_budget pass, no_more_leaks pass, gain pass

**`func/2/eff3` ships off.** The confirm seeds are spent.

phrase probe by separator, leaked words shipped -> `func/2/eff3`: dot 9 -> 9; hyphen 6 -> 6; space 391 -> 20; underscore 14 -> 14
connective probe by separator, leaked words shipped -> `func/2/eff3`: dot 33 -> 33; hyphen 64 -> 64; space 15 -> 15; underscore 61 -> 61
offlist_phrase probe by separator, leaked words shipped -> `func/2/eff3`: dot 0 -> 0; hyphen 10 -> 10; space 426 -> 426; underscore 21 -> 21
