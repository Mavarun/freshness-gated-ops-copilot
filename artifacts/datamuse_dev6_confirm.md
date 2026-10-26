# Word-meaning Datamuse arm: one-shot confirm on dev6 (pre-registered, `datamuse_dev6.py`)

Arm: rank<=100 n1 context>=2 sense>=0.30, on top of the shipped default. 45 dev6 rows (20 must-refuse), the 203-row run, the tests/ sweep and 36 attribute traps.

| | shipped default | + Datamuse arm |
| :--- | ---: | ---: |
| dev6 correct | 21/45 | 23/45 |
| dev6 ANSWER | 3/24 | 5/24 |
| dev6 must-refuse opened | 0 | d6-36 |
| 203-row clean / perturbed | 1.000 / 0.901 | 1.000 / 0.916 |
| held-out accuracy / ANSWER | 0.514 / 0 of 9 | 0.600 / 1 of 9 |
| attribute traps opened | 0/36 | 0/36 |
| fresh general-English set | 11/26 | 16/26 |

Fixed: d6-11 (What relief does the checkout latency runbook recommend?), d6-24 (What is the vault-transit key rotation custodian email?), d6-27 (How do we run the blue-green deploy protocol?).
New errors: d6-36 (What country is the checkout_retry feature flag from? -> ANSWER).
Sweep: 1 opened, labelled traps opened: none.
Exact sign test on changed dev6 rows (recorded only): 3 fixed vs 1 broken, p = 0.625.

| check | pass |
| :--- | :---: |
| confirm_gain | yes |
| confirm_answer_not_down | yes |
| confirm_no_new_error | **no** |
| confirm_no_fail_open_write_pii | **no** |
| clean_1 | yes |
| robustness_no_fail_open_write_pii | yes |
| heldout_acc_not_down | yes |
| heldout_answer_not_down | yes |
| confirm_must_refuse_held | **no** |
| sweep_no_labelled_trap | yes |
| attribute_traps_all_refused | yes |

**Decision: ships off.** dev6 is now spent.
