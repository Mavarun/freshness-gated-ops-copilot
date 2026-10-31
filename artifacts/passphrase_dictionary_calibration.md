# Passphrase dictionary / digit-guard arms: calibration (seeds 3109 / 3119 / 3121, 1,200 rows each; 3,025 SE train sentences, 1,920 SE train identifiers)

Pre-registered in `ops_copilot.passphrase_dictionary_protocol`. Arm = plain rule / scope / glued digit. `ops/compounds/off` is the shipped detector. Probe words: standard 5,954, attached 5,933, invented 6,016.

| arm | leak words std / glued / invented (total) | over words | SE sentences flagged | SE ids flagged (new) | Oct 13 / queries / data ids | safe |
| --- | ---: | ---: | ---: | ---: | ---: | :---: |
| ops/compounds/off | 4 / 2081 / 0 (2085) | 1455 | 28 | 221 (0) | 0 / 0 / 0 | yes |
| ops/compounds/raw | 4 / 16 / 0 (20) | 1525 | 29 | 233 (12) | 0 / 0 / 0 | no: se_identifiers |
| ops/compounds/guard | 4 / 16 / 0 (20) | 1525 | 28 | 221 (0) | 0 / 0 / 0 | yes |
| dict/compounds/off | 4 / 2081 / 1294 (3379) | 1455 | 28 | 48 (0) | 0 / 0 / 0 | no: invented_budget |
| dict/compounds/raw | 4 / 16 / 1294 (1314) | 1525 | 29 | 50 (2) | 0 / 0 / 0 | no: invented_budget |
| dict/compounds/guard | 4 / 16 / 1294 (1314) | 1525 | 28 | 48 (0) | 0 / 0 / 0 | no: invented_budget |
| dict/all/off | 4 / 2081 / 1294 (3379) | 1455 | 24 | 48 (0) | 0 / 0 / 0 | no: invented_budget |
| dict/all/raw | 4 / 16 / 1294 (1314) | 1525 | 25 | 50 (2) | 0 / 0 / 0 | no: invented_budget |
| dict/all/guard | 4 / 16 / 1294 (1314) | 1525 | 24 | 48 (0) | 0 / 0 / 0 | no: invented_budget |
| dict_cv/compounds/off | 4 / 2081 / 888 (2973) | 1455 | 28 | 53 (0) | 0 / 0 / 0 | no: invented_budget |
| dict_cv/compounds/raw | 4 / 16 / 888 (908) | 1525 | 29 | 55 (2) | 0 / 0 / 0 | no: invented_budget |
| dict_cv/compounds/guard | 4 / 16 / 888 (908) | 1525 | 28 | 53 (0) | 0 / 0 / 0 | no: invented_budget |
| dict_cv/all/off | 4 / 2081 / 888 (2973) | 1455 | 24 | 53 (0) | 0 / 0 / 0 | no: invented_budget |
| dict_cv/all/raw | 4 / 16 / 888 (908) | 1525 | 25 | 55 (2) | 0 / 0 / 0 | no: invented_budget |
| dict_cv/all/guard | 4 / 16 / 888 (908) | 1525 | 24 | 53 (0) | 0 / 0 / 0 | no: invented_budget |

**Chosen:** `ops/compounds/guard`

Leak causes, chosen: standard: other 1; attached: other 1, stop_inside 3; invented: 
