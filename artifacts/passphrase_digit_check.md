# attached_digit: one-shot check (pre-registered in `ops_copilot.passphrase_digit_protocol`)

| rows | leak rows (shipped -> knob) | leak words (shipped -> knob) | over-redacted |
| --- | ---: | ---: | ---: |
| Bitwarden shape, seed 3079 | 438 -> 3 of 1,200 | 1857 -> 7 of 5,905 | 507 -> 581 |
| Oct 29 shape, seed 3083 | 5 -> 5 | 21 -> 21 of 5,937 | 503 -> 503 |

Oct 13 probe leaks 0; trace queries changed 0; data/ ids newly flagged 0.
SE train: sentences flagged 28 -> 29 of 3,025; identifiers newly flagged 12 of 1,920 (shipped already flags 221): `Column1.deviceDetail.displayName`, `Diff-Ext-for-KDiff3`, `Shibboleth-IdP3-TOTP-Auth`, `diffie-hellman-group1-sha1`, `gvfs-udisks2-volume-monitor`, `kde4-ftps-kio`, `libgl1-mesa-dev`, `libgl1-mesa-dri`, `libgl1-mesa-glx`, `libxcb-glx0-dev`, `net.ipv4.conf.all`, `ssh2-enum-algos`.
SE test: sentences flagged 0 -> 0 of 306; identifiers newly flagged 1 of 147 (shipped already flags 24): `net.ipv6.conf.eth1.autoconf`.

Checks: attached_fewer_leaks pass, standard_no_more_leaks pass, standard_over_budget pass, oct13_no_leak pass, repo_queries_unchanged pass, data_idents pass, se_train_sentences pass, se_train_identifiers FAIL, se_test_sentences pass, se_test_identifiers pass

**Ships off.** Seeds 3079 and 3083 are spent.

Leak causes with the knob (Bitwarden rows): other 1, stop_inside 2

Still leaking (first few):

- `my password is Secret9 Applaud Landmass Audibly, why can't I log in?`
- `use Used Overheat Colt Lather7 Resource to log in to vault`
- `the deploy token Device Underwear Slander8 Unhappy Many stopped working, who rotates it?`
