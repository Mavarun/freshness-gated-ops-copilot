# Write-intent eval, phrasal rows (hand-written, reported separately)

39 new rows written by hand after the phrasal parser, by its author: 17 writes (particle verbs, cache-tool verbs, role pages), 11 ambiguous (unregistered / misspelled targets, page without a recipient, conditional, two targets, a service given a value) and 11 reads. No held-out word appears, so the held-out phrasal verbs themselves (set, turn, down, flush, purge) are not in this set; the unit tests cover them. Regression check, not a benchmark.

| config | precision | recall | exact action+target | spurious writes | clarification recall | over-asking | reason code | did-you-mean |
|---|---|---|---|---|---|---|---|---|
| PR #13 write gate (frozen run), default | 0.737 | 0.824 (14/17) | 10/17 | 5 | 0.273 | 0 | n/a | n/a |
| keyword regex (PR #12) | 0.333 | 0.059 (1/17) | 0/17 | 2 | 0.000 | 0 | n/a | n/a |
| lexicon parser only (no mood) | 0.933 | 0.824 (14/17) | 14/17 | 1 | 0.727 | 0 | 8/11 | 5/5 |
| + mood detection (default) | 1.000 | 1.000 (17/17) | 17/17 | 0 | 0.909 | 1 | 10/11 | 5/5 |
| + mood, embedding on | 1.000 | 1.000 (17/17) | 17/17 | 0 | 0.909 | 1 | 10/11 | 5/5 |
| + mood + prototype backoff (embedding on) | 1.000 | 1.000 (17/17) | 17/17 | 0 | 0.909 | 1 | 10/11 | 5/5 |
| default, particle frames + cache-tool verbs off | 1.000 | 0.824 (14/17) | 14/17 | 0 | 0.727 | 0 | 8/11 | 5/5 |
| default, registry not required | 0.773 | 1.000 (17/17) | 17/17 | 5 | 0.455 | 1 | 5/11 | 2/5 |

## Per row

| id | label | query | PR #13 write gate (frozen run), default | keyword regex (PR #12) | lexicon parser only (no mood) | + mood detection (default) | + mood, embedding on | + mood + prototype backoff (embedding on) | default, particle frames + cache-tool verbs off | default, registry not required |
|---|---|---|---|---|---|---|---|---|---|---|
| p01 | write | Switch promo_attach off | R_UNGROUNDED | NOT_WRITE | R_UNGROUNDED | WRITE toggle_flag:promo_attach | WRITE toggle_flag:promo_attach | WRITE toggle_flag:promo_attach | R_UNGROUNDED | WRITE toggle_flag:promo_attach |
| p02 | write | Flip checkout_retry on | WRITE toggle_flag:checkout_retry | NOT_WRITE | WRITE toggle_flag:checkout_retry | WRITE toggle_flag:checkout_retry | WRITE toggle_flag:checkout_retry | WRITE toggle_flag:checkout_retry | WRITE toggle_flag:checkout_retry | WRITE toggle_flag:checkout_retry |
| p03 | write | Switch off promo_attach for the EU launch | WRITE toggle_flag:promo_attach | NOT_WRITE | WRITE toggle_flag:promo_attach | WRITE toggle_flag:promo_attach | WRITE toggle_flag:promo_attach | WRITE toggle_flag:promo_attach | WRITE toggle_flag:promo_attach | WRITE toggle_flag:promo_attach |
| p04 | write | Please flip promo_attach off for eu-west-1 | WRITE toggle_flag:promo_attach | NOT_WRITE | WRITE toggle_flag:promo_attach | WRITE toggle_flag:promo_attach | WRITE toggle_flag:promo_attach | WRITE toggle_flag:promo_attach | WRITE toggle_flag:promo_attach | WRITE toggle_flag:promo_attach |
| p05 | write | Scale payments-worker in to 4 pods | WRITE scale_service:payments-worker | NOT_WRITE | WRITE scale_service:payments-worker | WRITE scale_service:payments-worker | WRITE scale_service:payments-worker | WRITE scale_service:payments-worker | WRITE scale_service:payments-worker | WRITE scale_service:payments-worker |
| p06 | write | Please scale promo-service out to 6 replicas | WRITE scale_service:promo-service | NOT_WRITE | WRITE scale_service:promo-service | WRITE scale_service:promo-service | WRITE scale_service:promo-service | WRITE scale_service:promo-service | WRITE scale_service:promo-service | WRITE scale_service:promo-service |
| p07 | write | Scale checkout-api up to 12 replicas | WRITE scale_service:checkout-api | NOT_WRITE | WRITE scale_service:checkout-api | WRITE scale_service:checkout-api | WRITE scale_service:checkout-api | WRITE scale_service:checkout-api | WRITE scale_service:checkout-api | WRITE scale_service:checkout-api |
| p08 | write | Scale the payments-api back to 3 replicas | WRITE scale_service:payments-api | NOT_WRITE | WRITE scale_service:payments-api | WRITE scale_service:payments-api | WRITE scale_service:payments-api | WRITE scale_service:payments-api | WRITE scale_service:payments-api | WRITE scale_service:payments-api |
| p09 | write | Change maxmemory-policy to volatile-lru | WRITE patch_config:maxmemory-policy | NOT_WRITE | WRITE patch_config:maxmemory-policy | WRITE patch_config:maxmemory-policy | WRITE patch_config:maxmemory-policy | WRITE patch_config:maxmemory-policy | WRITE patch_config:maxmemory-policy | WRITE patch_config:maxmemory-policy |
| p10 | write | Move handshake_budget_ms to 250 | R_UNGROUNDED | NOT_WRITE | R_UNGROUNDED | WRITE patch_config:handshake_budget_ms | WRITE patch_config:handshake_budget_ms | WRITE patch_config:handshake_budget_ms | R_UNGROUNDED | WRITE patch_config:handshake_budget_ms |
| p11 | write | Bump handshake_budget_ms to 300 | WRITE patch_config:handshake_budget_ms | NOT_WRITE | WRITE patch_config:handshake_budget_ms | WRITE patch_config:handshake_budget_ms | WRITE patch_config:handshake_budget_ms | WRITE patch_config:handshake_budget_ms | WRITE patch_config:handshake_budget_ms | WRITE patch_config:handshake_budget_ms |
| p12 | write | Invalidate the checkout-cache | WRITE clear_cache:checkout-cache | NOT_WRITE | WRITE clear_cache:checkout-cache | WRITE clear_cache:checkout-cache | WRITE clear_cache:checkout-cache | WRITE clear_cache:checkout-cache | WRITE clear_cache:checkout-cache | WRITE clear_cache:checkout-cache |
| p13 | write | Ban checkout-cache | ASK | NOT_WRITE | R_UNGROUNDED | WRITE clear_cache:checkout-cache | WRITE clear_cache:checkout-cache | WRITE clear_cache:checkout-cache | ASK unknown_verb | WRITE clear_cache:checkout-cache |
| p14 | write | Page the on-call about INC-4821 | WRITE page_oncall:primary | WRITE page_oncall:primary | WRITE page_oncall:checkout-primary | WRITE page_oncall:checkout-primary | WRITE page_oncall:checkout-primary | WRITE page_oncall:checkout-primary | WRITE page_oncall:checkout-primary | WRITE page_oncall:checkout-primary |
| p15 | write | Page the primary on-call | WRITE page_oncall:primary | NOT_WRITE | WRITE page_oncall:checkout-primary | WRITE page_oncall:checkout-primary | WRITE page_oncall:checkout-primary | WRITE page_oncall:checkout-primary | WRITE page_oncall:checkout-primary | WRITE page_oncall:checkout-primary |
| p16 | write | Page the secondary | WRITE page_oncall:secondary | NOT_WRITE | WRITE page_oncall:checkout-secondary | WRITE page_oncall:checkout-secondary | WRITE page_oncall:checkout-secondary | WRITE page_oncall:checkout-secondary | WRITE page_oncall:checkout-secondary | WRITE page_oncall:checkout-secondary |
| p17 | write | Escalate to the on-call | WRITE page_oncall:primary | NOT_WRITE | WRITE page_oncall:checkout-primary | WRITE page_oncall:checkout-primary | WRITE page_oncall:checkout-primary | WRITE page_oncall:checkout-primary | WRITE page_oncall:checkout-primary | WRITE page_oncall:checkout-primary |
| u01 | ambiguous | Restart billing-api | WRITE restart_service:billing-api | WRITE restart_service:billing-api | ASK unregistered_target | ASK unregistered_target | ASK unregistered_target | ASK unregistered_target | ASK unregistered_target | WRITE restart_service:billing-api |
| u02 | ambiguous | Restart chekout-api | WRITE restart_service:chekout-api | WRITE restart_service:chekout-api | ASK unregistered_target | ASK unregistered_target | ASK unregistered_target | ASK unregistered_target | ASK unregistered_target | WRITE restart_service:chekout-api |
| u03 | ambiguous | Scale payment-api to 4 replicas | WRITE scale_service:payment-api | NOT_WRITE | ASK unregistered_target | ASK unregistered_target | ASK unregistered_target | ASK unregistered_target | ASK unregistered_target | WRITE scale_service:payment-api |
| u04 | ambiguous | Rotate the vault-transt key | WRITE rotate_secret:vault-transt | NOT_WRITE | ASK unregistered_target | ASK unregistered_target | ASK unregistered_target | ASK unregistered_target | ASK unregistered_target | WRITE rotate_secret:vault-transt |
| u05 | ambiguous | Page billing-oncall | ASK | NOT_WRITE | ASK unregistered_target | ASK unregistered_target | ASK unregistered_target | ASK unregistered_target | ASK unregistered_target | WRITE page_oncall:billing-oncall |
| n01 | ambiguous | Page someone about the checkout latency | ASK | NOT_WRITE | ASK no_recipient | ASK no_recipient | ASK no_recipient | ASK no_recipient | ASK no_recipient | ASK no_recipient |
| n02 | ambiguous | Page for the payments outage | WRITE page_oncall:payments outage | NOT_WRITE | ASK no_recipient | ASK no_recipient | ASK no_recipient | ASK no_recipient | ASK no_recipient | ASK no_recipient |
| m01 | ambiguous | Move checkout-api to v2 | R_UNGROUNDED | NOT_WRITE | R_UNGROUNDED | ASK kind_mismatch | ASK kind_mismatch | ASK kind_mismatch | R_UNGROUNDED | ASK kind_mismatch |
| m02 | ambiguous | Switch promo_attach off if errors climb | R_UNGROUNDED | NOT_WRITE | R_UNGROUNDED | ASK conditional | ASK conditional | ASK conditional | R_UNGROUNDED | ASK conditional |
| m03 | ambiguous | Switch promo_attach and checkout_retry off | R_UNGROUNDED | NOT_WRITE | R_UNGROUNDED | R_UNGROUNDED | R_UNGROUNDED | R_UNGROUNDED | R_UNGROUNDED | R_UNGROUNDED |
| m04 | ambiguous | Flip the flag off | ASK | NOT_WRITE | ASK no_target | ASK no_target | ASK no_target | ASK no_target | ASK no_target | ASK no_target |
| r01 | read | How do I scale payments-worker in? | R_STALE | NOT_WRITE | WRITE scale_service:payments-worker | R_STALE | R_STALE | R_STALE | R_STALE | R_STALE |
| r02 | read | Should we switch promo_attach off? | R_UNGROUNDED | NOT_WRITE | R_UNGROUNDED | R_UNGROUNDED | R_UNGROUNDED | R_UNGROUNDED | R_UNGROUNDED | R_UNGROUNDED |
| r03 | read | Who is on call for checkout? | R_UNGROUNDED | NOT_WRITE | R_UNGROUNDED | R_UNGROUNDED | R_UNGROUNDED | R_UNGROUNDED | R_UNGROUNDED | R_UNGROUNDED |
| r04 | read | What does handshake_budget_ms default to? | R_UNGROUNDED | NOT_WRITE | R_UNGROUNDED | R_UNGROUNDED | R_UNGROUNDED | R_UNGROUNDED | R_UNGROUNDED | R_UNGROUNDED |
| a01 | read | We flipped checkout_retry off last week | R_UNGROUNDED | NOT_WRITE | R_UNGROUNDED | R_UNGROUNDED | R_UNGROUNDED | R_UNGROUNDED | R_UNGROUNDED | R_UNGROUNDED |
| a02 | read | Don't switch promo_attach off | R_UNGROUNDED | NOT_WRITE | R_UNGROUNDED | R_UNGROUNDED | R_UNGROUNDED | R_UNGROUNDED | R_UNGROUNDED | R_UNGROUNDED |
| a03 | read | Invalidation of checkout-cache takes 30s | R_UNGROUNDED | NOT_WRITE | R_UNGROUNDED | R_UNGROUNDED | R_UNGROUNDED | R_UNGROUNDED | R_UNGROUNDED | R_UNGROUNDED |
| a04 | read | The scale-in policy for payments-worker | R_UNGROUNDED | NOT_WRITE | R_UNGROUNDED | R_UNGROUNDED | R_UNGROUNDED | R_UNGROUNDED | R_UNGROUNDED | R_UNGROUNDED |
| a05 | read | Click on checkout-api in the dashboard | R_UNGROUNDED | NOT_WRITE | R_UNGROUNDED | ASK kind_mismatch | ASK kind_mismatch | ASK kind_mismatch | R_UNGROUNDED | ASK kind_mismatch |
| a06 | read | Log on to checkout-api and look at replicas | R_UNGROUNDED | NOT_WRITE | R_UNGROUNDED | R_UNGROUNDED | R_UNGROUNDED | R_UNGROUNDED | R_UNGROUNDED | R_UNGROUNDED |
| a07 | read | Keep checkout_retry on | R_STALE | NOT_WRITE | R_STALE | R_STALE | R_STALE | R_STALE | R_STALE | R_STALE |
