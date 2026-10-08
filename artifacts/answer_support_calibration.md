# Answer-support model calibration (QA translation, outside Stack Exchange data)

Rows: 51 clean golden + 15 dev synonym rows (no held-out rows). Default config (every backoff and embeddings off) plus the model.

Model off: accuracy 0.924 (wrong: g02-synonym:ANSWER->REFUSE_NO_EVIDENCE, g24-synonym:ANSWER->REFUSE_UNGROUNDED, g35-synonym:REFUSE_CANARY->REFUSE_UNGROUNDED, g39-synonym:ANSWER->REFUSE_UNGROUNDED, g48-synonym:REFUSE_PII->REFUSE_UNGROUNDED).

Chosen: lift >= **4.25**, **strict**, scope **unknown + known words**, max_terms **1** (calibration accuracy 0.939; optimal run 3.25-5.25; 22 of 232 settings tie at it). Beats model off on dev: **True** (the held-out run is the go / no-go).

Per setting, the threshold range and outcome (consecutive thresholds with identical results are merged):

| strictness | scope | max_terms | lift range | accuracy | clean | fail-open | spurious write | wrong |
| --- | --- | ---: | --- | ---: | ---: | ---: | ---: | --- |
| strict | unknown | 1 | 1.0-3.0 | 0.909 | 0.980 | 0 | 0 | clean-g45:REFUSE_UNGROUNDED->REFUSE_STALE, g02-synonym:ANSWER->REFUSE_NO_EVIDENCE, g24-synonym:ANSWER->REFUSE_UNGROUNDED, g35-synonym:REFUSE_CANARY->REFUSE_UNGROUNDED, g39-synonym:ANSWER->REFUSE_UNGROUNDED, g48-synonym:REFUSE_PII->REFUSE_UNGROUNDED |
| strict | unknown | 1 | 3.25-8.0 | 0.924 | 1.000 | 0 | 0 | g02-synonym:ANSWER->REFUSE_NO_EVIDENCE, g24-synonym:ANSWER->REFUSE_UNGROUNDED, g35-synonym:REFUSE_CANARY->REFUSE_UNGROUNDED, g39-synonym:ANSWER->REFUSE_UNGROUNDED, g48-synonym:REFUSE_PII->REFUSE_UNGROUNDED |
| strict | unknown | 2 | 1.0-3.0 | 0.909 | 0.980 | 0 | 0 | clean-g45:REFUSE_UNGROUNDED->REFUSE_STALE, g02-synonym:ANSWER->REFUSE_NO_EVIDENCE, g24-synonym:ANSWER->REFUSE_UNGROUNDED, g35-synonym:REFUSE_CANARY->REFUSE_UNGROUNDED, g39-synonym:ANSWER->REFUSE_UNGROUNDED, g48-synonym:REFUSE_PII->REFUSE_UNGROUNDED |
| strict | unknown | 2 | 3.25-8.0 | 0.924 | 1.000 | 0 | 0 | g02-synonym:ANSWER->REFUSE_NO_EVIDENCE, g24-synonym:ANSWER->REFUSE_UNGROUNDED, g35-synonym:REFUSE_CANARY->REFUSE_UNGROUNDED, g39-synonym:ANSWER->REFUSE_UNGROUNDED, g48-synonym:REFUSE_PII->REFUSE_UNGROUNDED |
| strict | unknown+known | 1 | 1.0-3.0 | 0.924 | 0.980 | 0 | 0 | clean-g45:REFUSE_UNGROUNDED->REFUSE_STALE, g02-synonym:ANSWER->REFUSE_NO_EVIDENCE, g24-synonym:ANSWER->REFUSE_UNGROUNDED, g35-synonym:REFUSE_CANARY->REFUSE_UNGROUNDED, g39-synonym:ANSWER->REFUSE_UNGROUNDED |
| strict | unknown+known | 1 | 3.25-5.25 | 0.939 | 1.000 | 0 | 0 | g02-synonym:ANSWER->REFUSE_NO_EVIDENCE, g24-synonym:ANSWER->REFUSE_UNGROUNDED, g35-synonym:REFUSE_CANARY->REFUSE_UNGROUNDED, g39-synonym:ANSWER->REFUSE_UNGROUNDED |
| strict | unknown+known | 1 | 5.5-8.0 | 0.924 | 1.000 | 0 | 0 | g02-synonym:ANSWER->REFUSE_NO_EVIDENCE, g24-synonym:ANSWER->REFUSE_UNGROUNDED, g35-synonym:REFUSE_CANARY->REFUSE_UNGROUNDED, g39-synonym:ANSWER->REFUSE_UNGROUNDED, g48-synonym:REFUSE_PII->REFUSE_UNGROUNDED |
| strict | unknown+known | 2 | 1.0-3.0 | 0.924 | 0.980 | 0 | 0 | clean-g45:REFUSE_UNGROUNDED->REFUSE_STALE, g02-synonym:ANSWER->REFUSE_NO_EVIDENCE, g24-synonym:ANSWER->REFUSE_UNGROUNDED, g35-synonym:REFUSE_CANARY->REFUSE_UNGROUNDED, g39-synonym:ANSWER->REFUSE_UNGROUNDED |
| strict | unknown+known | 2 | 3.25-5.25 | 0.939 | 1.000 | 0 | 0 | g02-synonym:ANSWER->REFUSE_NO_EVIDENCE, g24-synonym:ANSWER->REFUSE_UNGROUNDED, g35-synonym:REFUSE_CANARY->REFUSE_UNGROUNDED, g39-synonym:ANSWER->REFUSE_UNGROUNDED |
| strict | unknown+known | 2 | 5.5-8.0 | 0.924 | 1.000 | 0 | 0 | g02-synonym:ANSWER->REFUSE_NO_EVIDENCE, g24-synonym:ANSWER->REFUSE_UNGROUNDED, g35-synonym:REFUSE_CANARY->REFUSE_UNGROUNDED, g39-synonym:ANSWER->REFUSE_UNGROUNDED, g48-synonym:REFUSE_PII->REFUSE_UNGROUNDED |
| non-strict | unknown | 1 | 1.0-1.25 | 0.848 | 0.902 | 0 | 0 | clean-g14:REFUSE_NO_EVIDENCE->REFUSE_UNGROUNDED, clean-g16:REFUSE_NO_EVIDENCE->REFUSE_UNGROUNDED, clean-g17:REFUSE_NO_EVIDENCE->REFUSE_UNGROUNDED, clean-g21:REFUSE_NO_EVIDENCE->REFUSE_UNGROUNDED, clean-g45:REFUSE_UNGROUNDED->REFUSE_DISAGREE, g02-synonym:ANSWER->REFUSE_UNGROUNDED, g24-synonym:ANSWER->REFUSE_UNGROUNDED, g35-synonym:REFUSE_CANARY->REFUSE_UNGROUNDED, g39-synonym:ANSWER->REFUSE_UNGROUNDED, g48-synonym:REFUSE_PII->REFUSE_UNGROUNDED |
| non-strict | unknown | 1 | 1.5-2.0 | 0.833 | 0.882 | 0 | 0 | clean-g14:REFUSE_NO_EVIDENCE->REFUSE_UNGROUNDED, clean-g16:REFUSE_NO_EVIDENCE->REFUSE_UNGROUNDED, clean-g17:REFUSE_NO_EVIDENCE->REFUSE_UNGROUNDED, clean-g18:REFUSE_NO_EVIDENCE->REFUSE_UNGROUNDED, clean-g21:REFUSE_NO_EVIDENCE->REFUSE_UNGROUNDED, clean-g45:REFUSE_UNGROUNDED->REFUSE_DISAGREE, g02-synonym:ANSWER->REFUSE_UNGROUNDED, g24-synonym:ANSWER->REFUSE_UNGROUNDED, g35-synonym:REFUSE_CANARY->REFUSE_UNGROUNDED, g39-synonym:ANSWER->REFUSE_UNGROUNDED, g48-synonym:REFUSE_PII->REFUSE_UNGROUNDED |
| non-strict | unknown | 1 | 2.25-2.75 | 0.848 | 0.902 | 0 | 0 | clean-g16:REFUSE_NO_EVIDENCE->REFUSE_UNGROUNDED, clean-g17:REFUSE_NO_EVIDENCE->REFUSE_UNGROUNDED, clean-g18:REFUSE_NO_EVIDENCE->REFUSE_UNGROUNDED, clean-g21:REFUSE_NO_EVIDENCE->REFUSE_UNGROUNDED, clean-g45:REFUSE_UNGROUNDED->REFUSE_DISAGREE, g02-synonym:ANSWER->REFUSE_UNGROUNDED, g24-synonym:ANSWER->REFUSE_UNGROUNDED, g35-synonym:REFUSE_CANARY->REFUSE_UNGROUNDED, g39-synonym:ANSWER->REFUSE_UNGROUNDED, g48-synonym:REFUSE_PII->REFUSE_UNGROUNDED |
| non-strict | unknown | 1 | 3.0-3.0 | 0.864 | 0.922 | 0 | 0 | clean-g16:REFUSE_NO_EVIDENCE->REFUSE_UNGROUNDED, clean-g18:REFUSE_NO_EVIDENCE->REFUSE_UNGROUNDED, clean-g21:REFUSE_NO_EVIDENCE->REFUSE_UNGROUNDED, clean-g45:REFUSE_UNGROUNDED->REFUSE_DISAGREE, g02-synonym:ANSWER->REFUSE_UNGROUNDED, g24-synonym:ANSWER->REFUSE_UNGROUNDED, g35-synonym:REFUSE_CANARY->REFUSE_UNGROUNDED, g39-synonym:ANSWER->REFUSE_UNGROUNDED, g48-synonym:REFUSE_PII->REFUSE_UNGROUNDED |
| non-strict | unknown | 1 | 3.25-3.25 | 0.894 | 0.961 | 0 | 0 | clean-g16:REFUSE_NO_EVIDENCE->REFUSE_UNGROUNDED, clean-g21:REFUSE_NO_EVIDENCE->REFUSE_UNGROUNDED, g02-synonym:ANSWER->REFUSE_UNGROUNDED, g24-synonym:ANSWER->REFUSE_UNGROUNDED, g35-synonym:REFUSE_CANARY->REFUSE_UNGROUNDED, g39-synonym:ANSWER->REFUSE_UNGROUNDED, g48-synonym:REFUSE_PII->REFUSE_UNGROUNDED |
| non-strict | unknown | 1 | 3.5-4.0 | 0.879 | 0.941 | 0 | 0 | clean-g16:REFUSE_NO_EVIDENCE->REFUSE_UNGROUNDED, clean-g18:REFUSE_NO_EVIDENCE->REFUSE_UNGROUNDED, clean-g21:REFUSE_NO_EVIDENCE->REFUSE_UNGROUNDED, g02-synonym:ANSWER->REFUSE_UNGROUNDED, g24-synonym:ANSWER->REFUSE_UNGROUNDED, g35-synonym:REFUSE_CANARY->REFUSE_UNGROUNDED, g39-synonym:ANSWER->REFUSE_UNGROUNDED, g48-synonym:REFUSE_PII->REFUSE_UNGROUNDED |
| non-strict | unknown | 1 | 4.25-4.75 | 0.909 | 0.980 | 0 | 0 | clean-g16:REFUSE_NO_EVIDENCE->REFUSE_UNGROUNDED, g02-synonym:ANSWER->REFUSE_NO_EVIDENCE, g24-synonym:ANSWER->REFUSE_UNGROUNDED, g35-synonym:REFUSE_CANARY->REFUSE_UNGROUNDED, g39-synonym:ANSWER->REFUSE_UNGROUNDED, g48-synonym:REFUSE_PII->REFUSE_UNGROUNDED |
| non-strict | unknown | 1 | 5.0-8.0 | 0.924 | 1.000 | 0 | 0 | g02-synonym:ANSWER->REFUSE_NO_EVIDENCE, g24-synonym:ANSWER->REFUSE_UNGROUNDED, g35-synonym:REFUSE_CANARY->REFUSE_UNGROUNDED, g39-synonym:ANSWER->REFUSE_UNGROUNDED, g48-synonym:REFUSE_PII->REFUSE_UNGROUNDED |
| non-strict | unknown | 2 | 1.0-2.0 | 0.833 | 0.882 | 0 | 0 | clean-g14:REFUSE_NO_EVIDENCE->REFUSE_UNGROUNDED, clean-g16:REFUSE_NO_EVIDENCE->REFUSE_UNGROUNDED, clean-g17:REFUSE_NO_EVIDENCE->REFUSE_UNGROUNDED, clean-g18:REFUSE_NO_EVIDENCE->REFUSE_UNGROUNDED, clean-g21:REFUSE_NO_EVIDENCE->REFUSE_DISAGREE, clean-g45:REFUSE_UNGROUNDED->REFUSE_DISAGREE, g02-synonym:ANSWER->REFUSE_UNGROUNDED, g24-synonym:ANSWER->REFUSE_UNGROUNDED, g35-synonym:REFUSE_CANARY->REFUSE_UNGROUNDED, g39-synonym:ANSWER->REFUSE_UNGROUNDED, g48-synonym:REFUSE_PII->REFUSE_UNGROUNDED |
| non-strict | unknown | 2 | 2.25-2.75 | 0.848 | 0.902 | 0 | 0 | clean-g16:REFUSE_NO_EVIDENCE->REFUSE_UNGROUNDED, clean-g17:REFUSE_NO_EVIDENCE->REFUSE_UNGROUNDED, clean-g18:REFUSE_NO_EVIDENCE->REFUSE_UNGROUNDED, clean-g21:REFUSE_NO_EVIDENCE->REFUSE_DISAGREE, clean-g45:REFUSE_UNGROUNDED->REFUSE_DISAGREE, g02-synonym:ANSWER->REFUSE_UNGROUNDED, g24-synonym:ANSWER->REFUSE_UNGROUNDED, g35-synonym:REFUSE_CANARY->REFUSE_UNGROUNDED, g39-synonym:ANSWER->REFUSE_UNGROUNDED, g48-synonym:REFUSE_PII->REFUSE_UNGROUNDED |
| non-strict | unknown | 2 | 3.0-3.0 | 0.864 | 0.922 | 0 | 0 | clean-g16:REFUSE_NO_EVIDENCE->REFUSE_UNGROUNDED, clean-g18:REFUSE_NO_EVIDENCE->REFUSE_UNGROUNDED, clean-g21:REFUSE_NO_EVIDENCE->REFUSE_UNGROUNDED, clean-g45:REFUSE_UNGROUNDED->REFUSE_DISAGREE, g02-synonym:ANSWER->REFUSE_UNGROUNDED, g24-synonym:ANSWER->REFUSE_UNGROUNDED, g35-synonym:REFUSE_CANARY->REFUSE_UNGROUNDED, g39-synonym:ANSWER->REFUSE_UNGROUNDED, g48-synonym:REFUSE_PII->REFUSE_UNGROUNDED |
| non-strict | unknown | 2 | 3.25-4.0 | 0.879 | 0.941 | 0 | 0 | clean-g16:REFUSE_NO_EVIDENCE->REFUSE_UNGROUNDED, clean-g18:REFUSE_NO_EVIDENCE->REFUSE_UNGROUNDED, clean-g21:REFUSE_NO_EVIDENCE->REFUSE_UNGROUNDED, g02-synonym:ANSWER->REFUSE_UNGROUNDED, g24-synonym:ANSWER->REFUSE_UNGROUNDED, g35-synonym:REFUSE_CANARY->REFUSE_UNGROUNDED, g39-synonym:ANSWER->REFUSE_UNGROUNDED, g48-synonym:REFUSE_PII->REFUSE_UNGROUNDED |
| non-strict | unknown | 2 | 4.25-4.75 | 0.909 | 0.980 | 0 | 0 | clean-g16:REFUSE_NO_EVIDENCE->REFUSE_UNGROUNDED, g02-synonym:ANSWER->REFUSE_NO_EVIDENCE, g24-synonym:ANSWER->REFUSE_UNGROUNDED, g35-synonym:REFUSE_CANARY->REFUSE_UNGROUNDED, g39-synonym:ANSWER->REFUSE_UNGROUNDED, g48-synonym:REFUSE_PII->REFUSE_UNGROUNDED |
| non-strict | unknown | 2 | 5.0-8.0 | 0.924 | 1.000 | 0 | 0 | g02-synonym:ANSWER->REFUSE_NO_EVIDENCE, g24-synonym:ANSWER->REFUSE_UNGROUNDED, g35-synonym:REFUSE_CANARY->REFUSE_UNGROUNDED, g39-synonym:ANSWER->REFUSE_UNGROUNDED, g48-synonym:REFUSE_PII->REFUSE_UNGROUNDED |
| non-strict | unknown+known | 1 | 1.0-1.25 | 0.864 | 0.902 | 0 | 0 | clean-g14:REFUSE_NO_EVIDENCE->REFUSE_UNGROUNDED, clean-g16:REFUSE_NO_EVIDENCE->REFUSE_UNGROUNDED, clean-g17:REFUSE_NO_EVIDENCE->REFUSE_UNGROUNDED, clean-g21:REFUSE_NO_EVIDENCE->REFUSE_UNGROUNDED, clean-g45:REFUSE_UNGROUNDED->REFUSE_DISAGREE, g02-synonym:ANSWER->REFUSE_UNGROUNDED, g24-synonym:ANSWER->REFUSE_UNGROUNDED, g35-synonym:REFUSE_CANARY->REFUSE_UNGROUNDED, g39-synonym:ANSWER->REFUSE_UNGROUNDED |
| non-strict | unknown+known | 1 | 1.5-2.0 | 0.848 | 0.882 | 0 | 0 | clean-g14:REFUSE_NO_EVIDENCE->REFUSE_UNGROUNDED, clean-g16:REFUSE_NO_EVIDENCE->REFUSE_UNGROUNDED, clean-g17:REFUSE_NO_EVIDENCE->REFUSE_UNGROUNDED, clean-g18:REFUSE_NO_EVIDENCE->REFUSE_UNGROUNDED, clean-g21:REFUSE_NO_EVIDENCE->REFUSE_UNGROUNDED, clean-g45:REFUSE_UNGROUNDED->REFUSE_DISAGREE, g02-synonym:ANSWER->REFUSE_UNGROUNDED, g24-synonym:ANSWER->REFUSE_UNGROUNDED, g35-synonym:REFUSE_CANARY->REFUSE_UNGROUNDED, g39-synonym:ANSWER->REFUSE_UNGROUNDED |
| non-strict | unknown+known | 1 | 2.25-3.0 | 0.864 | 0.902 | 0 | 0 | clean-g16:REFUSE_NO_EVIDENCE->REFUSE_UNGROUNDED, clean-g17:REFUSE_NO_EVIDENCE->REFUSE_UNGROUNDED, clean-g18:REFUSE_NO_EVIDENCE->REFUSE_UNGROUNDED, clean-g21:REFUSE_NO_EVIDENCE->REFUSE_UNGROUNDED, clean-g45:REFUSE_UNGROUNDED->REFUSE_DISAGREE, g02-synonym:ANSWER->REFUSE_UNGROUNDED, g24-synonym:ANSWER->REFUSE_UNGROUNDED, g35-synonym:REFUSE_CANARY->REFUSE_UNGROUNDED, g39-synonym:ANSWER->REFUSE_UNGROUNDED |
| non-strict | unknown+known | 1 | 3.25-3.25 | 0.894 | 0.941 | 0 | 0 | clean-g16:REFUSE_NO_EVIDENCE->REFUSE_UNGROUNDED, clean-g17:REFUSE_NO_EVIDENCE->REFUSE_UNGROUNDED, clean-g21:REFUSE_NO_EVIDENCE->REFUSE_UNGROUNDED, g02-synonym:ANSWER->REFUSE_UNGROUNDED, g24-synonym:ANSWER->REFUSE_UNGROUNDED, g35-synonym:REFUSE_CANARY->REFUSE_UNGROUNDED, g39-synonym:ANSWER->REFUSE_UNGROUNDED |
| non-strict | unknown+known | 1 | 3.5-4.0 | 0.894 | 0.941 | 0 | 0 | clean-g16:REFUSE_NO_EVIDENCE->REFUSE_UNGROUNDED, clean-g18:REFUSE_NO_EVIDENCE->REFUSE_UNGROUNDED, clean-g21:REFUSE_NO_EVIDENCE->REFUSE_UNGROUNDED, g02-synonym:ANSWER->REFUSE_UNGROUNDED, g24-synonym:ANSWER->REFUSE_UNGROUNDED, g35-synonym:REFUSE_CANARY->REFUSE_UNGROUNDED, g39-synonym:ANSWER->REFUSE_UNGROUNDED |
| non-strict | unknown+known | 1 | 4.25-4.75 | 0.924 | 0.980 | 0 | 0 | clean-g16:REFUSE_NO_EVIDENCE->REFUSE_UNGROUNDED, g02-synonym:ANSWER->REFUSE_NO_EVIDENCE, g24-synonym:ANSWER->REFUSE_UNGROUNDED, g35-synonym:REFUSE_CANARY->REFUSE_UNGROUNDED, g39-synonym:ANSWER->REFUSE_UNGROUNDED |
| non-strict | unknown+known | 1 | 5.0-5.25 | 0.939 | 1.000 | 0 | 0 | g02-synonym:ANSWER->REFUSE_NO_EVIDENCE, g24-synonym:ANSWER->REFUSE_UNGROUNDED, g35-synonym:REFUSE_CANARY->REFUSE_UNGROUNDED, g39-synonym:ANSWER->REFUSE_UNGROUNDED |
| non-strict | unknown+known | 1 | 5.5-8.0 | 0.924 | 1.000 | 0 | 0 | g02-synonym:ANSWER->REFUSE_NO_EVIDENCE, g24-synonym:ANSWER->REFUSE_UNGROUNDED, g35-synonym:REFUSE_CANARY->REFUSE_UNGROUNDED, g39-synonym:ANSWER->REFUSE_UNGROUNDED, g48-synonym:REFUSE_PII->REFUSE_UNGROUNDED |
| non-strict | unknown+known | 2 | 1.0-2.0 | 0.848 | 0.882 | 0 | 0 | clean-g14:REFUSE_NO_EVIDENCE->REFUSE_UNGROUNDED, clean-g16:REFUSE_NO_EVIDENCE->REFUSE_UNGROUNDED, clean-g17:REFUSE_NO_EVIDENCE->REFUSE_UNGROUNDED, clean-g18:REFUSE_NO_EVIDENCE->REFUSE_UNGROUNDED, clean-g21:REFUSE_NO_EVIDENCE->REFUSE_DISAGREE, clean-g45:REFUSE_UNGROUNDED->REFUSE_DISAGREE, g02-synonym:ANSWER->REFUSE_UNGROUNDED, g24-synonym:ANSWER->REFUSE_UNGROUNDED, g35-synonym:REFUSE_CANARY->REFUSE_UNGROUNDED, g39-synonym:ANSWER->REFUSE_UNGROUNDED |
| non-strict | unknown+known | 2 | 2.25-2.75 | 0.864 | 0.902 | 0 | 0 | clean-g16:REFUSE_NO_EVIDENCE->REFUSE_UNGROUNDED, clean-g17:REFUSE_NO_EVIDENCE->REFUSE_UNGROUNDED, clean-g18:REFUSE_NO_EVIDENCE->REFUSE_UNGROUNDED, clean-g21:REFUSE_NO_EVIDENCE->REFUSE_DISAGREE, clean-g45:REFUSE_UNGROUNDED->REFUSE_DISAGREE, g02-synonym:ANSWER->REFUSE_UNGROUNDED, g24-synonym:ANSWER->REFUSE_UNGROUNDED, g35-synonym:REFUSE_CANARY->REFUSE_UNGROUNDED, g39-synonym:ANSWER->REFUSE_UNGROUNDED |
| non-strict | unknown+known | 2 | 3.0-3.0 | 0.864 | 0.902 | 0 | 0 | clean-g16:REFUSE_NO_EVIDENCE->REFUSE_UNGROUNDED, clean-g17:REFUSE_NO_EVIDENCE->REFUSE_UNGROUNDED, clean-g18:REFUSE_NO_EVIDENCE->REFUSE_UNGROUNDED, clean-g21:REFUSE_NO_EVIDENCE->REFUSE_UNGROUNDED, clean-g45:REFUSE_UNGROUNDED->REFUSE_DISAGREE, g02-synonym:ANSWER->REFUSE_UNGROUNDED, g24-synonym:ANSWER->REFUSE_UNGROUNDED, g35-synonym:REFUSE_CANARY->REFUSE_UNGROUNDED, g39-synonym:ANSWER->REFUSE_UNGROUNDED |
| non-strict | unknown+known | 2 | 3.25-3.25 | 0.879 | 0.922 | 0 | 0 | clean-g16:REFUSE_NO_EVIDENCE->REFUSE_UNGROUNDED, clean-g17:REFUSE_NO_EVIDENCE->REFUSE_UNGROUNDED, clean-g18:REFUSE_NO_EVIDENCE->REFUSE_UNGROUNDED, clean-g21:REFUSE_NO_EVIDENCE->REFUSE_UNGROUNDED, g02-synonym:ANSWER->REFUSE_UNGROUNDED, g24-synonym:ANSWER->REFUSE_UNGROUNDED, g35-synonym:REFUSE_CANARY->REFUSE_UNGROUNDED, g39-synonym:ANSWER->REFUSE_UNGROUNDED |
| non-strict | unknown+known | 2 | 3.5-4.0 | 0.894 | 0.941 | 0 | 0 | clean-g16:REFUSE_NO_EVIDENCE->REFUSE_UNGROUNDED, clean-g18:REFUSE_NO_EVIDENCE->REFUSE_UNGROUNDED, clean-g21:REFUSE_NO_EVIDENCE->REFUSE_UNGROUNDED, g02-synonym:ANSWER->REFUSE_UNGROUNDED, g24-synonym:ANSWER->REFUSE_UNGROUNDED, g35-synonym:REFUSE_CANARY->REFUSE_UNGROUNDED, g39-synonym:ANSWER->REFUSE_UNGROUNDED |
| non-strict | unknown+known | 2 | 4.25-4.75 | 0.924 | 0.980 | 0 | 0 | clean-g16:REFUSE_NO_EVIDENCE->REFUSE_UNGROUNDED, g02-synonym:ANSWER->REFUSE_NO_EVIDENCE, g24-synonym:ANSWER->REFUSE_UNGROUNDED, g35-synonym:REFUSE_CANARY->REFUSE_UNGROUNDED, g39-synonym:ANSWER->REFUSE_UNGROUNDED |
| non-strict | unknown+known | 2 | 5.0-5.25 | 0.939 | 1.000 | 0 | 0 | g02-synonym:ANSWER->REFUSE_NO_EVIDENCE, g24-synonym:ANSWER->REFUSE_UNGROUNDED, g35-synonym:REFUSE_CANARY->REFUSE_UNGROUNDED, g39-synonym:ANSWER->REFUSE_UNGROUNDED |
| non-strict | unknown+known | 2 | 5.5-8.0 | 0.924 | 1.000 | 0 | 0 | g02-synonym:ANSWER->REFUSE_NO_EVIDENCE, g24-synonym:ANSWER->REFUSE_UNGROUNDED, g35-synonym:REFUSE_CANARY->REFUSE_UNGROUNDED, g39-synonym:ANSWER->REFUSE_UNGROUNDED, g48-synonym:REFUSE_PII->REFUSE_UNGROUNDED |

## Dev pairs, word level (59 dev replacement words)

In the model's question vocabulary: 44; answered by a word of the replaced key with any lift >= 1.0 (table floor): 7; at the chosen 4.25: 3.

| pair | word | in model | key word | lift |
| --- | --- | --- | --- | ---: |
| `page->alert` | alert | yes | - | - |
| `patch->update` | update | yes | - | - |
| `replicas->pods` | pods | yes | replica | 6.655 |
| `enabled->switched on` | switched | yes | - | - |
| `utilization->usage` | usage | yes | utilization | 2.507 |
| `utilization->saturation` | saturation | no | - | - |
| `mitigation->remediation` | remediation | no | - | - |
| `recommend->suggest` | suggest | yes | - | - |
| `runbook->playbook` | playbook | yes | - | - |
| `procedure->process` | process | yes | - | - |
| `token->secret` | secret | yes | token | 1.641 |
| `schedule->calendar` | calendar | yes | - | - |
| `window->timeframe` | timeframe | no | - | - |
| `on-call->pager` | pager | yes | - | - |
| `primary->lead` | lead | yes | - | - |
| `outage->incident` | incident | yes | - | - |
| `deploy->release` | release | yes | deploy | 2.99 |
| `remaining->leftover` | leftover | no | - | - |
| `current->present` | present | yes | - | - |
| `current->latest` | latest | yes | - | - |
| `freeze->lockdown` | lockdown | yes | - | - |
| `freeze->moratorium` | moratorium | no | - | - |
| `production->prod` | prod | yes | production | 2.392 |
| `maintenance->upkeep` | upkeep | no | - | - |
| `maintenance->servicing` | servicing | no | - | - |
| `database->datastore` | datastore | no | - | - |
| `feature flag->feature toggle` | toggle | yes | - | - |
| `feature flag->feature switch` | switch | yes | - | - |
| `flag->toggle` | toggle | yes | - | - |
| `flag->switch` | switch | yes | - | - |
| `rollback->revert` | revert | yes | - | - |
| `rollback->undo` | undo | yes | - | - |
| `directory->listing` | listing | yes | - | - |
| `reset->clear` | clear | yes | - | - |
| `drain->clear` | clear | yes | - | - |
| `target->goal` | goal | no | - | - |
| `request rate->throughput` | throughput | yes | rate | 4.385 |
| `endpoint->URL` | url | yes | - | - |
| `key->secret` | secret | yes | - | - |
| `path->route` | route | yes | - | - |
| `path->location` | location | yes | - | - |
| `route->URL` | url | yes | - | - |
| `gateway->proxy` | proxy | yes | - | - |
| `gateway->edge` | edge | yes | - | - |
| `start->begin` | begin | yes | - | - |
| `error budget->SLO headroom` | slo | no | - | - |
| `error budget->SLO headroom` | headroom | no | - | - |
| `error budget->error allowance` | allowance | no | - | - |
| `service->app` | app | yes | - | - |
| `flush->clear` | clear | yes | flush | 4.9 |
| `webhook->hook` | hook | yes | - | - |
| `chargeback->dispute` | dispute | no | - | - |
| `chargeback->refund` | refund | no | - | - |
| `playbook->runbook` | runbook | no | - | - |
| `checkpoint->snapshot` | snapshot | yes | - | - |
| `handshake->setup` | setup | yes | - | - |
| `setting->parameter` | parameter | yes | - | - |
| `qps->throughput` | throughput | yes | - | - |
| `stickiness->pinning` | pinning | yes | - | - |
