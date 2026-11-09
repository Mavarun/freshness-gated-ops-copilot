# Non-key coverage rule, post-hoc reading (selects nothing; the confirm call stands)

## Answered rows `all` loses (5; 2 are a hyphen part of a cited token)

| phase | row | query | missing word | compound part of evidence |
| :--- | :--- | :--- | :--- | :--- |
| calibration | d5-22 | What is the Vault AppRole rotation cadence? | cadence | - |
| calibration | d6-06 | Who is the first on-call right now? | on-call | - |
| confirm | d8-06 | Who is the primary on-call right now for checkout? | checkout | checkout |
| confirm | d8-29 | Who is the primary on-call right now on the checkout rotation? | checkout | checkout |
| confirm | d8-30 | How many checkout-api replicas are running after the scale-up? | after | - |

## dev8 topic traps the shipped default opens (5)

| row | query | unsupported terms | how it passed | `all` |
| :--- | :--- | :--- | :--- | :--- |
| d8-t02 | Is the checkout_retry feature flag enabled in staging? | staging | non-key unsupported | REFUSE_UNGROUNDED |
| d8-t03 | Who is the primary on-call next month? | - | lexical | ANSWER |
| d8-t05 | What is the remaining error budget for payments? | payments | non-key unsupported | REFUSE_UNGROUNDED |
| d8-t08 | What is the status of the payments-api database? | - | lexical | ANSWER |
| d8-t12 | What is the vault-transit key rotation schedule for the checkout cluster? | checkout | non-key unsupported | REFUSE_UNGROUNDED |
