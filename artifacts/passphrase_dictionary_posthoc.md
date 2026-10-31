# Dictionary rule, post-hoc (spent rows; nothing ships from this)

| seed | words | arm | cv rows: leak rows / words | cvc rows: leak rows / words |
| --- | --- | --- | ---: | ---: |
| 3121 | invented | ops/compounds/off | 0 / 0 of 2990 | 0 / 0 of 3026 |
| 3121 | invented | dict/compounds/guard | 83 / 406 of 2990 | 177 / 888 of 3026 |
| 3121 | invented | dict_cv/compounds/guard | 0 / 0 of 2990 | 177 / 888 of 3026 |
| 3167 | invented | ops/compounds/off | 0 / 0 of 2965 | 0 / 0 of 3006 |
| 3167 | invented | dict/compounds/guard | 92 / 427 of 2965 | 182 / 920 of 3006 |
| 3167 | invented | dict_cv/compounds/guard | 0 / 0 of 2965 | 182 / 920 of 3006 |

Seed 3121, `dict/compounds/guard`, closed-syllable rows leaking by separator: dot 65 of 150, hyphen 57 of 150, space 0 of 150, underscore 55 of 150

Seed 3167, `dict/compounds/guard`, closed-syllable rows leaking by separator: dot 62 of 150, hyphen 63 of 150, space 0 of 150, underscore 57 of 150

SE train identifiers flagged by the shipped detector: 221.
- `dict/compounds/guard`: still flags 48; stops flagging 173 (all_caps 31, lower 105, mixed_case 37). Still flagged: `ALL_COL_PRIVS`, `COLA_MARKETS_MVIEW`, `COLA_MARKETS_VIEW`, `Candy-Crush-Free`, `Conventions-Transact-SQL`, `DRIVER_UNLOADED_WITHOUT_CANCELLING_PENDING_OPERATIONS`, `ERR_CONNECTION_TIMED_OUT`, `New-directories-with-files`
- `dict_cv/compounds/guard`: still flags 53; stops flagging 168 (all_caps 30, lower 101, mixed_case 37). Still flagged: `ALL_COL_PRIVS`, `COLA_MARKETS_MVIEW`, `COLA_MARKETS_VIEW`, `Candy-Crush-Free`, `Conventions-Transact-SQL`, `DRIVER_UNLOADED_WITHOUT_CANCELLING_PENDING_OPERATIONS`, `ERR_CONNECTION_TIMED_OUT`, `KUBE_SERVICE_ADDRESSES`
