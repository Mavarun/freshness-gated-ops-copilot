# dev6 post-hoc: what the Datamuse arm mapped (dev6 spent; selects nothing)

33 of 36 swap rows put a word the corpus does not know into the query; the arm maps a word in 8 of 45 rows. By hand: 3 right-sense, 5 wrong-sense mappings; 4 mapped rows change decision.

| row | query | expect | off -> on | query word -> corpus word | rank | cosine | context | sense |
| :--- | :--- | :--- | :--- | :--- | ---: | ---: | ---: | :--- |
| d6-09 | What is the available error budget for checkout? | ANSWER | ANSWER -> ANSWER | available -> availability | 7 | 0.81 | 3 | right |
| d6-11 | What relief does the checkout latency runbook recommend? | ANSWER | REFUSE_UNGROUNDED -> ANSWER | relief -> mitigation | 4 | 0.48 | 3 | right |
| d6-12 | What mitigation does the checkout latency runbook urge? | ANSWER | REFUSE_UNGROUNDED -> REFUSE_UNGROUNDED | urge -> request | 99 | 0.67 | 2 | wrong |
| d6-15 | What is the Redis checkout-pool occupation? | ANSWER | REFUSE_UNGROUNDED -> REFUSE_UNGROUNDED | occupation -> working | 35 | 0.39 | 2 | wrong |
| d6-20 | When does the production hold start? | ANSWER | ANSWER -> ANSWER | hold -> maintenance | 67 | 0.45 | 2 | wrong |
| d6-24 | What is the vault-transit key rotation custodian email? | ANSWER | REFUSE_UNGROUNDED -> ANSWER | custodian -> owner | 92 | 0.42 | 2 | right |
| d6-27 | How do we run the blue-green deploy protocol? | REFUSE_STALE | REFUSE_UNGROUNDED -> REFUSE_STALE | protocol -> minutes | 15 | 0.5 | 2 | wrong |
| d6-36 | What country is the checkout_retry feature flag from? | REFUSE_UNGROUNDED | REFUSE_UNGROUNDED -> ANSWER | country -> region | 12 | 0.45 | 3 | wrong |
