# Passphrase shape guards: one-shot confirm (seeds 3251 / 3253 / 3257 / 3259 / 3271, 1,200 rows each; 306 SE test sentences, 147 SE test identifiers)

Pick from calibration: `case+tld`. Never scored on these seeds or on SE test before this run.

| arm | leak words std / glued / invented / cased / phrase (total) | over words | SE sentences flagged | SE ids flagged (new) | Oct 13 / queries / data ids | checks |
| --- | ---: | ---: | ---: | ---: | ---: | :---: |
| shipped | 1 / 34 / 0 / 6 / 1273 (1314) | 2547 | 0 | 24 (0) | 0 / 0 / 0 | yes |
| case+tld | 1 / 34 / 0 / 6 / 1273 (1314) | 2547 | 0 | 21 (0) | 0 / 0 / 0 | yes |

Checks: oct13_no_leak pass, repo_queries_unchanged pass, data_idents pass, se_sentences pass, se_identifiers pass, over_budget pass, strict_no_more_leaks pass, leak_budget pass, fewer_test_identifiers pass

**Ships on.** The confirm seeds are spent.

SE test identifiers flagged: 24 -> 21 of 147 (no longer flagged: `DatabaseName.SchemaName.TableName`, `blogs.FreeBSDish.org`, `centos.pkgs.org`).

Rows leaking, shipped -> pick: standard 1 -> 1; attached 9 -> 9; invented 0 -> 0; cased 2 -> 2; phrase 368 -> 368

Off-list control (seed 3299, reported only): leaked words 14 -> 14 of 5,967.
