# Credited-word check: one-shot confirm (pre-registered, `credit_check.py`)

Arm: stop=True, top_freq=0, max_rank=0 on the shipped default (null test seed 42, q = 0.30, sticky).

| rows never seen while designing | shipped default | credited-word arm |
| :--- | ---: | ---: |
| v3 confirm traps opened | 0/19 (-) | 0/19 (-) |
| dev7 confirm correct / ANSWER | 5/18 / 2 of 13 | 5/18 / 2 of 13 |
| 203-row clean / perturbed | 1.000 / 0.901 | 1.000 / 0.901 |
| held-out accuracy / ANSWER | 0.514 / 0 of 9 | 0.514 / 0 of 9 |
| fresh general-English set (recorded) | 0.423 (1/11) | 0.385 (1/11) |

dev7 confirm: fixed none; new errors none; exact sign test (recorded only) p = 1.000.
Robustness rows that change: none.
Sweep: 0 opened, labelled traps opened: none.

Checks: traps_v3_confirm_none_open pass, dev7_confirm_no_new_error pass, dev7_confirm_no_must_refuse_open pass, clean_1 pass, robustness_no_fail_open_write_pii pass, heldout_acc_not_down pass, heldout_answer_not_down pass, perturbed_within_2_rows pass, sweep_no_labelled_trap pass.

**Default on: yes.**
