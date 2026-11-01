# Passphrase shape guards: calibration (seeds 3203 / 3209 / 3217 / 3221 / 3229, 1,200 rows each; 3,025 SE train sentences, 1,920 SE train identifiers)

Pre-registered in `ops_copilot.passphrase_shape_protocol`. `shipped` is the Oct 31 detector. Probe words: standard 5,980, attached 5,933, invented 5,988, cased 5,952, phrase 4,758.

| arm | leak words std / glued / invented / cased / phrase (total) | over words | SE sentences flagged | SE ids flagged (new) | Oct 13 / queries / data ids | checks |
| --- | ---: | ---: | ---: | ---: | ---: | :---: |
| shipped | 15 / 17 / 0 / 7 / 1252 (1291) | 2495 | 28 | 221 (0) | 0 / 0 / 0 | yes |
| case | 15 / 17 / 0 / 7 / 1252 (1291) | 2495 | 28 | 197 (0) | 0 / 0 / 0 | yes |
| tld | 15 / 17 / 0 / 7 / 1252 (1291) | 2495 | 28 | 188 (0) | 0 / 0 / 0 | yes |
| stop | 15 / 17 / 0 / 7 / 1649 (1688) | 2495 | 28 | 198 (0) | 0 / 0 / 0 | no: leak_budget |
| case+tld | 15 / 17 / 0 / 7 / 1252 (1291) | 2495 | 28 | 166 (0) | 0 / 0 / 0 | yes |
| case+stop | 15 / 17 / 0 / 7 / 1649 (1688) | 2495 | 28 | 174 (0) | 0 / 0 / 0 | no: leak_budget |
| tld+stop | 15 / 17 / 0 / 7 / 1649 (1688) | 2495 | 28 | 165 (0) | 0 / 0 / 0 | no: leak_budget |
| case+tld+stop | 15 / 17 / 0 / 7 / 1649 (1688) | 2495 | 28 | 143 (0) | 0 / 0 / 0 | no: leak_budget |

**Chosen:** `case+tld`

SE train identifiers no longer flagged: 55 (by guard, a name can hit several: case 24, tld 33). Examples: `AmazonEKS_CNI_Policy`, `JobA.StepA.VariableA`, `KernelBase.dll.mui`, `Microsoft.VisualStudio.Shell.Interop`, `MultiRBL.valli.org`, `User.ReadWrite.All`, `WebStorm.exe.vmoptions`, `Whonix-Gateway-LXQt`

Still flagged (first few): `ACCOUNTID.dkr.ecr`, `ALL_COL_PRIVS`, `ASYNC_DISKPOOL_LOCK`, `AUTO_UPDATE_STATISTCS_ASYNC`, `Adj-RIB-Out`, `BTRFS_FIRST_FREE_OBJECTID`, `BTRFS_LAST_FREE_OBJECTID`, `CLSCTX_INPROC_SERVER`

Leak causes, chosen: standard: stop_inside 3; attached: other 3, stop_inside 1; invented: none; cased: stop_inside 2; phrase: no_flag_ops 16, other 279, stop_inside 1, tail_trim 74
