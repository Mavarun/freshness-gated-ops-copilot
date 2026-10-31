# Passphrase dictionary / digit-guard: one-shot confirm (seeds 3137 / 3163 / 3167, 1,200 rows each; 306 SE test sentences, 147 SE test identifiers)

Pick from calibration: `ops/compounds/guard`. Never scored on these seeds or on SE test before this run.

| arm | leak words std / glued / invented (total) | over words | SE sentences flagged | SE ids flagged (new) | Oct 13 / queries / data ids | safe |
| --- | ---: | ---: | ---: | ---: | ---: | :---: |
| ops/compounds/off | 12 / 1948 / 0 (1960) | 1516 | 0 | 24 (0) | 0 / 0 / 0 | yes |
| ops/compounds/guard | 12 / 10 / 0 (22) | 1575 | 0 | 24 (0) | 0 / 0 / 0 | yes |

Checks: oct13_no_leak pass, repo_queries_unchanged pass, data_idents pass, se_sentences pass, se_identifiers pass, standard_no_more_leaks pass, invented_budget pass, over_budget pass, gain pass

**Ships on.** The confirm seeds are spent.

Rows leaking, shipped -> pick: standard 3 -> 3; attached 456 -> 4; invented 0 -> 0

Leak causes with the pick: standard: no_flag_ops 1, stop_inside 2; attached: no_flag_ops 1, other 1, stop_inside 2; invented: none

Off-list control (seed 3181, reported only): leaked words 15 -> 15 of 5,948.

Glued-digit rows still leaking (first few):

- `use many.stable.unsavory.outnumber3 to log in to vault`
- `the deploy token Armhole Gumming7 Earwig Coherence Expiring stopped working, who rotates it?`
- `log in to grafana with passphrase bonanza botanist hesitancy2 many please`
- `The vault passphrase is setting.opt9.haven.islamist.good. Who owns vault-transit?`
