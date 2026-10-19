# WordNet coverage of missed noun swaps (post-hoc, dev2-chosen arm)

| set | no_link | outside_gate | mapped_still_wrong | correct | not_applicable |
| :--- | ---: | ---: | ---: | ---: | ---: |
| dev2 | 7 | 4 | 0 | 23 | 1 |
| fresh | 6 | 1 | 1 | 15 | 3 |

| set | row | swap | bucket | WordNet link (path, relation, sense rank) |
| :--- | :--- | :--- | :--- | :--- |
| dev2 | d2-01 | latency -> delay | no_link | - |
| dev2 | d2-03 | feature -> capability | no_link | - |
| dev2 | d2-05 | replicas -> copies | outside_gate | 1, hypo, 1 |
| dev2 | d2-08 | mitigation -> countermeasure | no_link | - |
| dev2 | d2-10 | utilization -> occupancy | no_link | - |
| dev2 | d2-11 | utilization -> load | no_link | - |
| dev2 | d2-18 | rotation -> turnover | no_link | - |
| dev2 | d2-19 | rotation -> changeover | no_link | - |
| dev2 | d2-20 | contact -> liaison | outside_gate | 0, syn, 1 |
| dev2 | d2-21 | procedure -> routine | outside_gate | 0, syn, 2 |
| dev2 | d2-26 | replicas -> copies | outside_gate | 1, hypo, 1 |
| fresh | f03 | primary -> principal | no_link | - |
| fresh | f06 | mitigation -> remedy | no_link | - |
| fresh | f07 | utilization -> consumption | no_link | - |
| fresh | f08 | status -> condition | mapped_still_wrong | 0, syn, 0 |
| fresh | f10 | start -> commence | no_link | - |
| fresh | f21 | path -> pathway | outside_gate | 1, hyper, 1 |
| fresh | f25 | budget -> allotment | no_link | - |
| fresh | f26 | cadence -> periodicity | no_link | - |
