# Tag-synonym backoff calibration (Stack Exchange tag synonyms)

Rows: 51 clean golden + 15 dev synonym rows (no held-out rows). Default config (embedding off, word-vector backoff off) plus the backoff.

Backoff off: accuracy 0.924 (wrong: g02-synonym:ANSWER->REFUSE_NO_EVIDENCE, g24-synonym:ANSWER->REFUSE_UNGROUNDED, g35-synonym:REFUSE_CANARY->REFUSE_UNGROUNDED, g39-synonym:ANSWER->REFUSE_UNGROUNDED, g48-synonym:REFUSE_PII->REFUSE_UNGROUNDED).

Chosen: sites **ops**, min_sites **3**, max_neighbours **1**, scope **unknown words only** (calibration accuracy 0.924; 24 of 24 settings tie at it). Beats backoff off on dev: **False** (the held-out run is the go / no-go).

| sites | min_sites | scope | max_neighbours | accuracy | clean | fail-open | spurious write | wrong |
| --- | ---: | --- | ---: | ---: | ---: | ---: | ---: | --- |
| ops | 1 | unknown | 1 | 0.924 | 1.000 | 0 | 0 | g02-synonym:ANSWER->REFUSE_NO_EVIDENCE, g24-synonym:ANSWER->REFUSE_UNGROUNDED, g35-synonym:REFUSE_CANARY->REFUSE_UNGROUNDED, g39-synonym:ANSWER->REFUSE_UNGROUNDED, g48-synonym:REFUSE_PII->REFUSE_UNGROUNDED |
| ops | 1 | unknown | 3 | 0.924 | 1.000 | 0 | 0 | g02-synonym:ANSWER->REFUSE_NO_EVIDENCE, g24-synonym:ANSWER->REFUSE_UNGROUNDED, g35-synonym:REFUSE_CANARY->REFUSE_UNGROUNDED, g39-synonym:ANSWER->REFUSE_UNGROUNDED, g48-synonym:REFUSE_PII->REFUSE_UNGROUNDED |
| ops | 1 | unknown+known | 1 | 0.924 | 1.000 | 0 | 0 | g02-synonym:ANSWER->REFUSE_NO_EVIDENCE, g24-synonym:ANSWER->REFUSE_UNGROUNDED, g35-synonym:REFUSE_CANARY->REFUSE_UNGROUNDED, g39-synonym:ANSWER->REFUSE_UNGROUNDED, g48-synonym:REFUSE_PII->REFUSE_UNGROUNDED |
| ops | 1 | unknown+known | 3 | 0.924 | 1.000 | 0 | 0 | g02-synonym:ANSWER->REFUSE_NO_EVIDENCE, g24-synonym:ANSWER->REFUSE_UNGROUNDED, g35-synonym:REFUSE_CANARY->REFUSE_UNGROUNDED, g39-synonym:ANSWER->REFUSE_UNGROUNDED, g48-synonym:REFUSE_PII->REFUSE_UNGROUNDED |
| ops | 2 | unknown | 1 | 0.924 | 1.000 | 0 | 0 | g02-synonym:ANSWER->REFUSE_NO_EVIDENCE, g24-synonym:ANSWER->REFUSE_UNGROUNDED, g35-synonym:REFUSE_CANARY->REFUSE_UNGROUNDED, g39-synonym:ANSWER->REFUSE_UNGROUNDED, g48-synonym:REFUSE_PII->REFUSE_UNGROUNDED |
| ops | 2 | unknown | 3 | 0.924 | 1.000 | 0 | 0 | g02-synonym:ANSWER->REFUSE_NO_EVIDENCE, g24-synonym:ANSWER->REFUSE_UNGROUNDED, g35-synonym:REFUSE_CANARY->REFUSE_UNGROUNDED, g39-synonym:ANSWER->REFUSE_UNGROUNDED, g48-synonym:REFUSE_PII->REFUSE_UNGROUNDED |
| ops | 2 | unknown+known | 1 | 0.924 | 1.000 | 0 | 0 | g02-synonym:ANSWER->REFUSE_NO_EVIDENCE, g24-synonym:ANSWER->REFUSE_UNGROUNDED, g35-synonym:REFUSE_CANARY->REFUSE_UNGROUNDED, g39-synonym:ANSWER->REFUSE_UNGROUNDED, g48-synonym:REFUSE_PII->REFUSE_UNGROUNDED |
| ops | 2 | unknown+known | 3 | 0.924 | 1.000 | 0 | 0 | g02-synonym:ANSWER->REFUSE_NO_EVIDENCE, g24-synonym:ANSWER->REFUSE_UNGROUNDED, g35-synonym:REFUSE_CANARY->REFUSE_UNGROUNDED, g39-synonym:ANSWER->REFUSE_UNGROUNDED, g48-synonym:REFUSE_PII->REFUSE_UNGROUNDED |
| ops | 3 | unknown | 1 | 0.924 | 1.000 | 0 | 0 | g02-synonym:ANSWER->REFUSE_NO_EVIDENCE, g24-synonym:ANSWER->REFUSE_UNGROUNDED, g35-synonym:REFUSE_CANARY->REFUSE_UNGROUNDED, g39-synonym:ANSWER->REFUSE_UNGROUNDED, g48-synonym:REFUSE_PII->REFUSE_UNGROUNDED |
| ops | 3 | unknown | 3 | 0.924 | 1.000 | 0 | 0 | g02-synonym:ANSWER->REFUSE_NO_EVIDENCE, g24-synonym:ANSWER->REFUSE_UNGROUNDED, g35-synonym:REFUSE_CANARY->REFUSE_UNGROUNDED, g39-synonym:ANSWER->REFUSE_UNGROUNDED, g48-synonym:REFUSE_PII->REFUSE_UNGROUNDED |
| ops | 3 | unknown+known | 1 | 0.924 | 1.000 | 0 | 0 | g02-synonym:ANSWER->REFUSE_NO_EVIDENCE, g24-synonym:ANSWER->REFUSE_UNGROUNDED, g35-synonym:REFUSE_CANARY->REFUSE_UNGROUNDED, g39-synonym:ANSWER->REFUSE_UNGROUNDED, g48-synonym:REFUSE_PII->REFUSE_UNGROUNDED |
| ops | 3 | unknown+known | 3 | 0.924 | 1.000 | 0 | 0 | g02-synonym:ANSWER->REFUSE_NO_EVIDENCE, g24-synonym:ANSWER->REFUSE_UNGROUNDED, g35-synonym:REFUSE_CANARY->REFUSE_UNGROUNDED, g39-synonym:ANSWER->REFUSE_UNGROUNDED, g48-synonym:REFUSE_PII->REFUSE_UNGROUNDED |
| all | 1 | unknown | 1 | 0.924 | 1.000 | 0 | 0 | g02-synonym:ANSWER->REFUSE_NO_EVIDENCE, g24-synonym:ANSWER->REFUSE_UNGROUNDED, g35-synonym:REFUSE_CANARY->REFUSE_UNGROUNDED, g39-synonym:ANSWER->REFUSE_UNGROUNDED, g48-synonym:REFUSE_PII->REFUSE_UNGROUNDED |
| all | 1 | unknown | 3 | 0.924 | 1.000 | 0 | 0 | g02-synonym:ANSWER->REFUSE_NO_EVIDENCE, g24-synonym:ANSWER->REFUSE_UNGROUNDED, g35-synonym:REFUSE_CANARY->REFUSE_UNGROUNDED, g39-synonym:ANSWER->REFUSE_UNGROUNDED, g48-synonym:REFUSE_PII->REFUSE_UNGROUNDED |
| all | 1 | unknown+known | 1 | 0.924 | 1.000 | 0 | 0 | g02-synonym:ANSWER->REFUSE_NO_EVIDENCE, g24-synonym:ANSWER->REFUSE_UNGROUNDED, g35-synonym:REFUSE_CANARY->REFUSE_UNGROUNDED, g39-synonym:ANSWER->REFUSE_UNGROUNDED, g48-synonym:REFUSE_PII->REFUSE_UNGROUNDED |
| all | 1 | unknown+known | 3 | 0.924 | 1.000 | 0 | 0 | g02-synonym:ANSWER->REFUSE_NO_EVIDENCE, g24-synonym:ANSWER->REFUSE_UNGROUNDED, g35-synonym:REFUSE_CANARY->REFUSE_UNGROUNDED, g39-synonym:ANSWER->REFUSE_UNGROUNDED, g48-synonym:REFUSE_PII->REFUSE_UNGROUNDED |
| all | 2 | unknown | 1 | 0.924 | 1.000 | 0 | 0 | g02-synonym:ANSWER->REFUSE_NO_EVIDENCE, g24-synonym:ANSWER->REFUSE_UNGROUNDED, g35-synonym:REFUSE_CANARY->REFUSE_UNGROUNDED, g39-synonym:ANSWER->REFUSE_UNGROUNDED, g48-synonym:REFUSE_PII->REFUSE_UNGROUNDED |
| all | 2 | unknown | 3 | 0.924 | 1.000 | 0 | 0 | g02-synonym:ANSWER->REFUSE_NO_EVIDENCE, g24-synonym:ANSWER->REFUSE_UNGROUNDED, g35-synonym:REFUSE_CANARY->REFUSE_UNGROUNDED, g39-synonym:ANSWER->REFUSE_UNGROUNDED, g48-synonym:REFUSE_PII->REFUSE_UNGROUNDED |
| all | 2 | unknown+known | 1 | 0.924 | 1.000 | 0 | 0 | g02-synonym:ANSWER->REFUSE_NO_EVIDENCE, g24-synonym:ANSWER->REFUSE_UNGROUNDED, g35-synonym:REFUSE_CANARY->REFUSE_UNGROUNDED, g39-synonym:ANSWER->REFUSE_UNGROUNDED, g48-synonym:REFUSE_PII->REFUSE_UNGROUNDED |
| all | 2 | unknown+known | 3 | 0.924 | 1.000 | 0 | 0 | g02-synonym:ANSWER->REFUSE_NO_EVIDENCE, g24-synonym:ANSWER->REFUSE_UNGROUNDED, g35-synonym:REFUSE_CANARY->REFUSE_UNGROUNDED, g39-synonym:ANSWER->REFUSE_UNGROUNDED, g48-synonym:REFUSE_PII->REFUSE_UNGROUNDED |
| all | 3 | unknown | 1 | 0.924 | 1.000 | 0 | 0 | g02-synonym:ANSWER->REFUSE_NO_EVIDENCE, g24-synonym:ANSWER->REFUSE_UNGROUNDED, g35-synonym:REFUSE_CANARY->REFUSE_UNGROUNDED, g39-synonym:ANSWER->REFUSE_UNGROUNDED, g48-synonym:REFUSE_PII->REFUSE_UNGROUNDED |
| all | 3 | unknown | 3 | 0.924 | 1.000 | 0 | 0 | g02-synonym:ANSWER->REFUSE_NO_EVIDENCE, g24-synonym:ANSWER->REFUSE_UNGROUNDED, g35-synonym:REFUSE_CANARY->REFUSE_UNGROUNDED, g39-synonym:ANSWER->REFUSE_UNGROUNDED, g48-synonym:REFUSE_PII->REFUSE_UNGROUNDED |
| all | 3 | unknown+known | 1 | 0.924 | 1.000 | 0 | 0 | g02-synonym:ANSWER->REFUSE_NO_EVIDENCE, g24-synonym:ANSWER->REFUSE_UNGROUNDED, g35-synonym:REFUSE_CANARY->REFUSE_UNGROUNDED, g39-synonym:ANSWER->REFUSE_UNGROUNDED, g48-synonym:REFUSE_PII->REFUSE_UNGROUNDED |
| all | 3 | unknown+known | 3 | 0.924 | 1.000 | 0 | 0 | g02-synonym:ANSWER->REFUSE_NO_EVIDENCE, g24-synonym:ANSWER->REFUSE_UNGROUNDED, g35-synonym:REFUSE_CANARY->REFUSE_UNGROUNDED, g39-synonym:ANSWER->REFUSE_UNGROUNDED, g48-synonym:REFUSE_PII->REFUSE_UNGROUNDED |

## Dev pairs, word level (63 dev replacement words)

Tag table (all sites, 1 site, top 3) offers a word of the replaced key first: **0/63**; a key word but not first: 0; only other words: 0; nothing: 63.

| pair | word | substitutes | kind |
| --- | --- | --- | --- |
| `page->alert` | alert | - | none |
| `patch->update` | update | - | none |
| `replicas->pods` | pods | - | none |
| `replicas->instances` | instances | - | none |
| `enabled->switched on` | switched | - | none |
| `utilization->usage` | usage | - | none |
| `utilization->saturation` | saturation | - | none |
| `mitigation->remediation` | remediation | - | none |
| `recommend->suggest` | suggest | - | none |
| `runbook->playbook` | playbook | - | none |
| `procedure->process` | process | - | none |
| `email->e-mail` | e-mail | - | none |
| `token->secret` | secret | - | none |
| `schedule->calendar` | calendar | - | none |
| `window->timeframe` | timeframe | - | none |
| `on-call->on-duty` | on-duty | - | none |
| `on-call->pager` | pager | - | none |
| `primary->lead` | lead | - | none |
| `outage->incident` | incident | - | none |
| `deploy->release` | release | - | none |
| `remaining->leftover` | leftover | - | none |
| `current->present` | present | - | none |
| `current->latest` | latest | - | none |
| `freeze->lockdown` | lockdown | - | none |
| `freeze->moratorium` | moratorium | - | none |
| `production->prod` | prod | - | none |
| `maintenance->upkeep` | upkeep | - | none |
| `maintenance->servicing` | servicing | - | none |
| `database->datastore` | datastore | - | none |
| `feature flag->feature toggle` | toggle | - | none |
| `feature flag->feature switch` | switch | - | none |
| `flag->toggle` | toggle | - | none |
| `flag->switch` | switch | - | none |
| `rollback->revert` | revert | - | none |
| `rollback->undo` | undo | - | none |
| `owns->maintains` | maintains | - | none |
| `directory->listing` | listing | - | none |
| `reset->clear` | clear | - | none |
| `drain->clear` | clear | - | none |
| `target->goal` | goal | - | none |
| `request rate->throughput` | throughput | - | none |
| `endpoint->URL` | url | - | none |
| `key->secret` | secret | - | none |
| `path->route` | route | - | none |
| `path->location` | location | - | none |
| `route->URL` | url | - | none |
| `gateway->proxy` | proxy | - | none |
| `gateway->edge` | edge | - | none |
| `start->begin` | begin | - | none |
| `error budget->SLO headroom` | slo | - | none |
| `error budget->SLO headroom` | headroom | - | none |
| `error budget->error allowance` | allowance | - | none |
| `service->app` | app | - | none |
| `flush->clear` | clear | - | none |
| `webhook->hook` | hook | - | none |
| `chargeback->dispute` | dispute | - | none |
| `chargeback->refund` | refund | - | none |
| `playbook->runbook` | runbook | - | none |
| `checkpoint->snapshot` | snapshot | - | none |
| `handshake->setup` | setup | - | none |
| `setting->parameter` | parameter | - | none |
| `qps->throughput` | throughput | - | none |
| `stickiness->pinning` | pinning | - | none |
