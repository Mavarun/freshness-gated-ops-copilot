# Credential-request advice (2026-11-25)

Rules: `credential_advice_protocol.py`, written before the advice was coded.

| arm | decisions changed | ANSWER rows advised | legit advised | regression advised | Nov 25 coverage | Nov 24 coverage | passes |
| :--- | ---: | ---: | ---: | ---: | ---: | ---: | :--- |
| `wide` | 0 | 0 | 0 | 1 | 15 / 15 | 5 / 5 | True |
| `shipped` | 0 | 0 | 0 | 1 | 9 / 15 | 5 / 5 | False |

- `wide`: missed Nov 25 none; missed Nov 24 none; regression rows advised: d8-t07.
- `shipped`: missed Nov 25 cc-09, cc-10, cc-11, cc-13, cc-15, cc-16; missed Nov 24 none; regression rows advised: d8-t07.

**Ships: `wide`.**
