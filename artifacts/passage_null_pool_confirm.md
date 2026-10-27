# Seed-free null test: one-shot confirm (pre-registered, `passage_null_pool.py`)

Arm: whole-pool percentile, q = 0.40, sticky. Baseline: the shipped default (seed-42 sample, q = 0.30).

| rows (never seen while designing) | shipped default | pool arm |
| :--- | ---: | ---: |
| v2 confirm traps opened | 1/20 (at2-01) | 1/20 (at2-01) |
| 203-row clean / perturbed | 1.000 / 0.901 | 1.000 / 0.901 |
| held-out accuracy / ANSWER | 0.514 / 0 | 0.514 / 0 |
| dev6 (spent, recorded only) correct / ANSWER | 21/45 / 3 | 20/45 / 2 |

Shipped default over 10,000 control samples: P(at least one v2 confirm trap opens) = 0.990 (4 of 20 rows reach the null test).

Checks: clean_1 pass, heldout_acc_not_down pass, heldout_answer_not_down pass, perturbed_within_2_rows pass, robustness_no_fail_open_write_pii pass, sweep_no_labelled_trap pass, traps_v2_confirm_none_open **FAIL**.

**Default on: no.**
