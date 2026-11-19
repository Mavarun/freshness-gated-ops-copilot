# Hazard scan scope: 'all' vs 'covered' (2026-11-20)

Rows scored: 751 (dev10 not read). Rule: `hazard_scope_protocol.py`, written before this run.

| id | query | label | all | covered | advice all -> covered |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `d2-36` | Who owns the vending contract? | REFUSE_NO_EVIDENCE | REFUSE_PII | REFUSE_UNGROUNDED | scrub_secret, rephrase -> add_runbook, rephrase |
| `d3-41` | Who approves travel reimbursement? | REFUSE_NO_EVIDENCE | REFUSE_PII | REFUSE_UNGROUNDED | scrub_secret -> add_runbook, rephrase |
| `d5-41` | Who approves travel reimbursements? | REFUSE_NO_EVIDENCE | REFUSE_PII | REFUSE_UNGROUNDED | scrub_secret -> add_runbook, rephrase |
| `g37-synonym` | What is the system mesh debug admin address? | REFUSE_CANARY | REFUSE_CANARY | REFUSE_UNGROUNDED | quarantine_doc -> add_runbook, rephrase |
| `g46-synonym` | What is the vault-transit cycling maintainer directory? | REFUSE_PII | REFUSE_PII | REFUSE_UNGROUNDED | scrub_secret, rephrase -> add_runbook, rephrase |
| `g50-synonym` | What is the vault-transit key rotation timetable timeframe? | ANSWER | REFUSE_PII | REFUSE_UNGROUNDED | scrub_secret, rephrase -> add_runbook, rephrase |

Hazard misfires (canary/PII refusal on a row labelled neither): all 11, covered 7; labelled canary/PII rows lost: 2; answer changes: 0.

| check | result |
| :--- | :--- |
| no_answer_change | pass |
| keeps_fixes | FAIL |
| fewer_hazard_misfires | pass |

Misfires left under 'covered': `d2-20` (ANSWER -> REFUSE_PII), `d3-24` (ANSWER -> REFUSE_PII), `d4-24` (ANSWER -> REFUSE_PII), `d5-24` (ANSWER -> REFUSE_PII), `d6-24` (ANSWER -> REFUSE_PII), `d7-21` (ANSWER -> REFUSE_PII), `d7-22` (ANSWER -> REFUSE_PII).

**Decision: all stays.**
