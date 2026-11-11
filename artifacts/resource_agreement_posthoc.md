# Resource-agreement backoff, post-hoc reading (selects nothing)

Read after the calibration picked nothing; the confirm was not run. Held-out pairs are read only because the go / no-go is decided.

| split | single-word pairs | gold word gets >= 2 votes | >= 3 votes | top agreed (>= 2) is gold | top agreed (>= 2) is wrong |
| :--- | ---: | ---: | ---: | ---: | ---: |
| dev | 57 | 8 | 3 | 7 | 22 |
| heldout | 53 | 8 | 3 | 7 | 11 |

Ops pairs the README names (held-out): `restart->reboot` gold votes 0, top `bounce` (1); `restart->bounce` gold votes 0, top `climb` (1); `restart->recycle` gold votes 0, top `None` (0); `latency->lag` gold votes 1, top `behind` (1); `cadence->frequency` gold votes 1, top `cadence` (1)

Rows `agree2_lone` newly answers: d2-13 `What is the situation of the payments-api?` (expect ANSWER; situation -> status); d4-06 `Who is the chief on-call right now?` (expect ANSWER; chief -> executive); d4-19 `What is the production overhaul change window?` (expect ANSWER; overhaul -> maintenance); d4-22 `What is the Vault AppRole rotation itinerary?` (expect ANSWER; itinerary -> path); d5-04 `Is the checkout_retry feature marker enabled?` (expect ANSWER; marker -> flag); d8-28 `Is the checkout_retry feature flag enabled for customers?` (expect ANSWER; customers -> consumer)
Rows `agree3_all` newly answers: d2-13 `What is the situation of the payments-api?` (expect ANSWER; situation -> status); d2-20 `What is the vault-transit key rotation liaison email?` (expect ANSWER; liaison -> contact); d4-22 `What is the Vault AppRole rotation itinerary?` (expect ANSWER; itinerary -> path); d8-28 `Is the checkout_retry feature flag enabled for customers?` (expect ANSWER; customers -> consumer)
