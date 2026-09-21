# Eval report (PII redaction gate)

| metric | value |
| --- | --- |
| n | 51 |
| decision_accuracy | 1.000 |
| refusal_precision | 1.000 |
| refusal_recall | 1.000 |
| answer_grounding_rate | 1.000 |
| pii_precision | 1.000 |
| pii_recall | 1.000 |
| pii_f1 | 1.000 |
| n_pii_labeled | 5 |

Policy: unauthorized email/phone → REFUSE_PII; authorize allowlist → masked ANSWER; aws_key/slack_token → always REFUSE_PII.
