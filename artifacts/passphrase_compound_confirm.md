# Passphrase list / purpose arms: one-shot confirm (seed 3037, 1,200 EFF rows; 306 SE test sentences, 142 SE test identifiers)

Pick from calibration: `all4/space/num`. The shipped detector already flags 23 of the 142 test identifiers.

| arm | leak rows | leak words | over words | SE sentences flagged | SE identifiers newly flagged | Oct 13 leaks | repo query changes | data/ ids new | safe |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | :---: |
| none/-/- | 24 | 128 | 507 | 0 | 0 | 0 | 0 | 0 | yes |
| all4/space/num | 4 | 16 | 509 | 0 | 1 | 0 | 0 | 0 | yes |

Confirm checks: oct13_no_leak pass, repo_queries_unchanged pass, fp_budget pass, ident_budget pass, over_budget pass, data_idents pass, fewer_leaked_words pass

**Ships on.** Seed 3037 is spent.

Leak causes, shipped: no_flag_ops 5, other 16, stop_inside 3

Leak causes, pick: other 1, stop_inside 3

Off-list control (seed 3053, WordNet nouns not on the EFF list; reported, not gating): leak words 63 -> 33 of 5990, leak rows 12 -> 7, over-redacted 515 -> 515.

New SE test identifier flags: `client_header_buffer_size`
