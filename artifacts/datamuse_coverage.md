# Datamuse coverage of noun swaps (post-hoc, dev2-chosen arm: lone, rank<=10, n2)

| set | single swaps | linked rank<=10 | <=20 | <=50 | <=100 | no_link | outside_gate | mapped_still_wrong | correct | not_applicable | fixed without the link |
| :--- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| dev2 | 28 | 11 | 12 | 16 | 18 | 4 | 4 | 1 | 25 | 1 | 2 |
| fresh | 16 | 10 | 10 | 11 | 12 | 2 | 2 | 1 | 19 | 2 | 0 |

Rows WordNet had no link for:

| set | WordNet no-link rows | Datamuse link rank<=10 | rank<=100 | correct under the arm |
| :--- | ---: | ---: | ---: | ---: |
| dev2 | 7 | 1 | 4 | 2 |
| fresh | 6 | 2 | 4 | 2 |

| set | row | swap | Datamuse rank | gate maps to | bucket | WordNet bucket |
| :--- | :--- | :--- | ---: | :--- | :--- | :--- |
| dev2 | d2-01 | latency -> delay | 9 | wait, latency | correct | no_link |
| dev2 | d2-03 | feature -> capability | 26 | capacity | outside_gate | no_link |
| dev2 | d2-05 | replicas -> copies | 3 | replicas, superseded | mapped_still_wrong | outside_gate |
| dev2 | d2-06 | budget -> margin | - | edge | correct | correct |
| dev2 | d2-07 | error -> fault | 5 | error | correct | correct |
| dev2 | d2-08 | mitigation -> countermeasure | - | - | no_link | no_link |
| dev2 | d2-09 | runbook -> manual | - | playbook | correct | correct |
| dev2 | d2-10 | utilization -> occupancy | - | - | no_link | no_link |
| dev2 | d2-11 | utilization -> load | - | - | no_link | no_link |
| dev2 | d2-12 | status -> standing | - | - | no_link | correct |
| dev2 | d2-13 | status -> situation | 13 | posted, posts | correct (fixed without the link) | correct |
| dev2 | d2-15 | maintenance -> repair | 10 | maintenance | correct | correct |
| dev2 | d2-16 | freeze -> halt | 7 | freeze | correct | correct |
| dev2 | d2-17 | schedule -> plan | 35 | chart | outside_gate | correct |
| dev2 | d2-18 | rotation -> turnover | 57 | size | correct (fixed without the link) | no_link |
| dev2 | d2-19 | rotation -> changeover | 23 | changing | outside_gate | no_link |
| dev2 | d2-20 | contact -> liaison | 9 | handshake, coordinating | outside_gate | outside_gate |
| dev2 | d2-21 | procedure -> routine | 4 | runbook, procedure | correct | outside_gate |
| dev2 | d2-23 | ttl -> lifetime | - | omar | correct | correct |
| dev2 | d2-24 | ttl -> expiry | - | - | correct | correct |
| dev2 | d2-25 | target -> benchmark | 51 | - | correct | correct |
| dev2 | d2-26 | replicas -> copies | 3 | replicas, superseded | correct | outside_gate |
| dev2 | d2-27 | procedure -> routine | 4 | runbook, procedure | correct | correct |
| dev2 | d2-28 | playbook -> manual | 1 | playbook | correct | correct |
| dev2 | d2-29 | feature -> capability | 26 | capacity | correct | correct |
| dev2 | d2-38 | route -> destination | - | - | correct | correct |
| dev2 | d2-39 | admin -> administrator | 2 | executive, admin | correct | correct |
| dev2 | d2-42 | service -> application | - | executive | correct | correct |
| fresh | f03 | primary -> principal | 1 | corpus, primary | correct | no_link |
| fresh | f05 | remaining -> residual | 10 | remainder, remaining | correct | correct |
| fresh | f06 | mitigation -> remedy | - | - | no_link | no_link |
| fresh | f07 | utilization -> consumption | 39 | - | outside_gate | no_link |
| fresh | f08 | status -> condition | 2 | status | mapped_still_wrong | mapped_still_wrong |
| fresh | f09 | window -> slot | - | - | correct | correct |
| fresh | f10 | start -> commence | 2 | start, starts | correct | no_link |
| fresh | f11 | schedule -> agenda | 1 | schedule | correct | correct |
| fresh | f14 | target -> aim | 1 | target, targeting | correct | correct |
| fresh | f15 | drain -> empty | - | - | correct | correct |
| fresh | f17 | password -> passcode | 5 | password | correct | correct |
| fresh | f18 | procedure -> method | 7 | procedure, modulo | correct | correct |
| fresh | f19 | playbook -> handbook | 3 | playbook, document | correct | correct |
| fresh | f21 | path -> pathway | 6 | via, path | correct | outside_gate |
| fresh | f25 | budget -> allotment | 52 | - | outside_gate | no_link |
| fresh | f26 | cadence -> periodicity | - | - | no_link | no_link |
