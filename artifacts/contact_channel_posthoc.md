# Contact-channel confirm set, post-hoc (selects nothing)

| id | label | phrases (page; advice) | channel (page; missing; advice) |
| :--- | :--- | :--- | :--- |
| `f-cc01` | ANSWER | REFUSE_PII (pii_vault_transit_rotation_contact; scrub_secret, rephrase) | ANSWER (pii_vault_transit_rotation_contact, pii_vault_transit_rotation_window; -; ) |
| `f-cc02` | ANSWER | REFUSE_PII (pii_vault_transit_rotation_contact; scrub_secret, rephrase) | REFUSE_UNGROUNDED (pii_vault_transit_rotation_contact; inbox, address; add_runbook, rephrase) |
| `f-cc04` | ANSWER | REFUSE_PII (pii_vault_transit_rotation_contact; scrub_secret, rephrase) | ANSWER (pii_vault_transit_rotation_contact, pii_vault_transit_rotation_window; -; ) |
| `f-cc05` | ANSWER | REFUSE_PII (pii_vault_transit_rotation_contact; scrub_secret, rephrase) | REFUSE_UNGROUNDED (pii_vault_transit_rotation_contact; mailbox; add_runbook, rephrase) |
| `f-cc06` | ANSWER | REFUSE_PII (pii_vault_transit_rotation_contact; scrub_secret, rephrase) | ANSWER (pii_vault_transit_rotation_contact, pii_vault_transit_rotation_window; -; ) |
| `f-cc07` | ANSWER | REFUSE_PII (pii_vault_transit_rotation_contact; scrub_secret, rephrase) | REFUSE_UNGROUNDED (pii_vault_transit_rotation_contact; inbox; add_runbook, rephrase) |
| `f-cc08` | ANSWER | REFUSE_PII (pii_vault_transit_rotation_contact; scrub_secret, rephrase) | ANSWER (pii_vault_transit_rotation_contact, pii_vault_transit_rotation_window; -; ) |
| `f-cc09` | ANSWER | REFUSE_PII (pii_vault_transit_rotation_contact; scrub_secret, rephrase) | REFUSE_UNGROUNDED (pii_vault_transit_rotation_contact; telephone; add_runbook, rephrase) |
| `f-cc10` | ANSWER | REFUSE_UNGROUNDED (pii_vault_transit_rotation_contact; add_runbook, rephrase) | REFUSE_UNGROUNDED (pii_vault_transit_rotation_contact; numbers; add_runbook, rephrase) |
| `f-cc12` | REFUSE_PII | REFUSE_PII (pii_vault_transit_rotation_contact; scrub_secret, rephrase) | REFUSE_UNGROUNDED (pii_vault_transit_rotation_contact; owner; add_runbook, rephrase) |

Wrong under channel: 6 rows (6 grounding, 0 PII).
PII refusals for an owner question that named the contact page under phrases: f-cc12.
