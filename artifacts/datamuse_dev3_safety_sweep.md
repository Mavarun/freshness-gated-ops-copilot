# dev3-chosen Datamuse arm: changed decisions on every unit-test query literal

Arm: {'context_min': 2, 'max_neighbours': 2, 'max_rank': 50, 'scope': 'lone'}. Queries: 140; changed: 6; refusal -> ANSWER/PROPOSE_WRITE: 4; labelled traps opened: 1. Ships: **off (a labelled unit-test trap opens)**.

| query | default | arm | opened | expected (asserted in) |
| --- | --- | --- | :---: | --- |
| Is the checkout tardiness flag enabled? | REFUSE_UNGROUNDED | ANSWER | yes | unlabelled |
| What is the checkout p99 delay? | REFUSE_STALE | REFUSE_DISAGREE | - | unlabelled |
| What is the checkout p99 lag? | REFUSE_UNGROUNDED | ANSWER | yes | unlabelled |
| What is the current checkout p99 delay? | REFUSE_STALE | ANSWER | yes | unlabelled |
| What is the current checkout p99 lag? | REFUSE_UNGROUNDED | REFUSE_DISAGREE | - | unlabelled |
| What is the revert procedure for the checkout_retry feature toggle? | REFUSE_UNGROUNDED | ANSWER | yes | REFUSE_UNGROUNDED (tests/test_synonyms.py::test_synonyms_do_not_open_ungrounded_traps) |
