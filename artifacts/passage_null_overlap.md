# Can any whole-pool percentile cut separate traps from keep rows? (post-hoc, `passage_null_overlap.py`)

Rows: 247 (171 calibration, 36 + 40 attribute traps; all spent). Pool mode, sticky, cut grid 0.000-1.000 step 0.002.

Worst trap: open up to q = 0.408. ANSWER rows that pool mode keeps only at or below that cut: 6 (d2-17, d3-02, d3-09, d3-10, d3-23, d5-02). Free and safe cuts: 0.

| must-refuse row | opens up to q | calls (query word <- credited passage word, pool percentile) |
| :--- | ---: | :--- |
| at2-01 | 0.408 | taste <- one 0.408; taste <- bot 0.646; taste <- bot 0.646 |
| at-22 | 0.362 | flavour <- rolling 0.826; flavour <- two 0.363; flavour <- two 0.363 |
| at-12 | 0.302 | flavour <- other 0.303; flavour <- other 0.303 |
| at-33 | 0.228 | expensive <- adds 0.230; expensive <- adds 0.230 |
| at-01 | 0.212 | shape <- region 0.213; shape <- region 0.213 |
| at-21 | 0.212 | shape <- region 0.213; shape <- region 0.213 |
| at2-19 | 0.150 | accent <- percent 0.152; accent <- rule 0.325; accent <- rule 0.325 |
| at-25 | 0.128 | weight <- utc 0.129; weight <- only 0.617; weight <- utc 0.129 |
| d5-38 | 0.098 | colour <- default 0.099; colour <- default 0.099 |
| at-07 | 0.066 | price <- percent 0.067; price <- percent 0.067 |

| ANSWER row | kept up to q | calls |
| :--- | ---: | :--- |
| d5-02 | 0.118 | existing <- starting 0.460; existing <- snapshot 0.241; existing <- snapshot 0.120; existing <- deploy 0.631; existing <- starting 0.460 |
| d3-09 | 0.210 | unused <- remaining 0.212; unused <- page 0.635; unused <- page 0.635 |
| d2-17 | 0.344 | plan <- schedule 0.346; plan <- schedule 0.565; plan <- schedule 0.346 |
| d3-02 | 0.348 | today <- only 0.730; today <- time 0.350; today <- last 0.599; today <- bad 0.759; today <- only 0.730 |
| d3-23 | 0.402 | renewal <- rotation 0.402; renewal <- rotation 0.970; renewal <- rotation 0.970 |
| d3-10 | 0.408 | quota <- remaining 0.409; quota <- remaining 0.409 |
| d2-09 | 0.498 | manual <- flag 0.871; manual <- checkout 0.499; manual <- page 0.598; manual <- flag 0.871 |

Every trap that opens is credited by a generic passage word (`one`, `two`, `other`, `only`, `percent`, `adds`, `region`, `default`, `rolling`, `bot`, `utc`, `rule`). Most keep rows at the same percentiles are credited by a real substitute (`schedule`, `remaining`, `rotation`), but not all: d3-02 rides `today <- only / time / bad` and d2-09 `manual <- flag / checkout`. The percentile measures how much the passage prefers the word, not whether the credited word means the same thing, so no cut separates them (labels by hand, one person's judgement).
