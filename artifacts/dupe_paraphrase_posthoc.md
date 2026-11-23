# Duplicate-paraphrase backoff, post-hoc reading (selects nothing)

Read after the calibration picked nothing; the confirm was not run. Held-out pairs are read only because the go / no-go is decided.

| split | single-word pairs | pair in table | in table, key is a corpus word | strict: gold passes | strict: top is gold | strict: top is wrong | loose: gold passes | loose: top is gold | loose: top is wrong |
| :--- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| dev | 54 | 6 | 6 | 2 | 2 | 15 | 4 | 3 | 20 |
| heldout | 53 | 8 | 7 | 2 | 1 | 10 | 2 | 1 | 15 |

Ops pairs the README names (held-out; table numbers G² / cross / same, then the top strict candidate):

- `restart->reboot`: G² 200.913, cross 38, same 8 (`restart` is not a corpus word); strict top `off`, loose top `off`
- `restart->bounce`: not in the table (`restart` is not a corpus word); strict top `None`, loose top `None`
- `restart->recycle`: not in the table (`restart` is not a corpus word); strict top `None`, loose top `None`
- `latency->lag`: not in the table; strict top `None`, loose top `None`
- `status->health`: not in the table; strict top `None`, loose top `None`
- `rotation->cycling`: not in the table; strict top `None`, loose top `None`
- `schedule->timetable`: not in the table; strict top `None`, loose top `None`
- `cadence->frequency`: not in the table; strict top `None`, loose top `memory`

New random swaps answered by `strict_known` (4): golden-24 `production` -> `set` (table maps it to `change`); golden-50 `key` -> `identity` (table maps it to `key`); d2-14 `change` -> `set` (table maps it to `change`); d2-14 `span` -> `rules` (table maps it to `page`)
New random swaps answered by `loose_lone` (7): golden-06 `utilization` -> `hours` (table maps it to `time`); golden-24 `production` -> `set` (table maps it to `change`); golden-50 `key` -> `identity` (table maps it to `key`); d2-14 `change` -> `set` (table maps it to `change`); d2-14 `span` -> `rules` (table maps it to `page`); d2-16 `halt` -> `starting` (table maps it to `start`); d4-10 `remaining` -> `var` (table maps it to `error`)
New random swaps answered by `loose_all` (11): golden-00 `p99` -> `connection` (table maps it to `traffic`); golden-06 `utilization` -> `hours` (table maps it to `time`); golden-24 `production` -> `set` (table maps it to `change`); golden-50 `key` -> `identity` (table maps it to `key`); d2-09 `mitigation` -> `error` (table maps it to `var`); d2-14 `change` -> `set` (table maps it to `change`); d2-14 `span` -> `rules` (table maps it to `page`); d2-16 `halt` -> `starting` (table maps it to `start`); d3-11 `checkout` -> `default` (table maps it to `order`); d4-10 `remaining` -> `var` (table maps it to `error`); d4-10 `budget` -> `var` (table maps it to `error`)
