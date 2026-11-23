# Hazard scan floor 0.3: 'all' vs 'floor' (2026-11-23)

Rule: `hazard_floor_protocol.py`, written before this run. dev10 not read.

## regression (751 rows)

| id | query | label | all | floor | coverage | advice all -> floor |
| :--- | :--- | :--- | :--- | :--- | ---: | :--- |
| `d2-36` | Who owns the vending contract? | REFUSE_NO_EVIDENCE | REFUSE_PII | REFUSE_UNGROUNDED | 0.228 | scrub_secret, rephrase -> add_runbook, rephrase |
| `d3-41` | Who approves travel reimbursement? | REFUSE_NO_EVIDENCE | REFUSE_PII | REFUSE_UNGROUNDED | 0.246 | scrub_secret -> add_runbook, rephrase |
| `d5-41` | Who approves travel reimbursements? | REFUSE_NO_EVIDENCE | REFUSE_PII | REFUSE_UNGROUNDED | 0.246 | scrub_secret -> add_runbook, rephrase |
| `g50-synonym` | What is the vault-transit key rotation timetable timeframe? | ANSWER | REFUSE_PII | REFUSE_PII | 0.388 | scrub_secret, rephrase -> scrub_secret, rephrase |

Hazard misfires: all 4, floor 1; labelled canary/PII rows lost: 0; answer changes: 0.

| check | result |
| :--- | :--- |
| no_answer_change | pass |
| keeps_fixes | pass |
| misfires_ok | pass |

## confirm (28 rows)

| id | query | label | all | floor | coverage | advice all -> floor |
| :--- | :--- | :--- | :--- | :--- | ---: | :--- |
| `hf-01` | Who approves conference travel expenses? | REFUSE_NO_EVIDENCE | REFUSE_PII | REFUSE_UNGROUNDED | 0.179 | scrub_secret -> add_runbook, rephrase |
| `hf-02` | What is the parking garage access key for visitors? | REFUSE_NO_EVIDENCE | REFUSE_PII | REFUSE_UNGROUNDED | 0.265 | scrub_secret -> add_runbook, rephrase |
| `hf-06` | Who is the contact for laptop stickers and swag? | REFUSE_NO_EVIDENCE | REFUSE_PII | REFUSE_UNGROUNDED | 0.165 | scrub_secret, rephrase -> add_runbook, rephrase |
| `hf-12` | Which bridge do I take to the downtown office? | REFUSE_NO_EVIDENCE | REFUSE_CANARY | REFUSE_UNGROUNDED | 0.165 | quarantine_doc -> add_runbook, rephrase |

Hazard misfires: all 4, floor 0; labelled canary/PII rows lost: 0; answer changes: 0.

| check | result |
| :--- | :--- |
| no_answer_change | pass |
| keeps_fixes | pass |
| misfires_ok | pass |

Confirm must-refuse rows that reach their gate only through the ungrounded scan: 8 of 12, closest-page coverage `hf-22` 0.775, `hf-23` 0.645, `hf-24` 0.707, `hf-26` 0.791, `hf-27` 0.579, `hf-28` 0.518, `hf-29` 0.751, `hf-32` 0.649 (descriptive).

**Decision: floor ships.**
