# Word-vector backoff calibration (counter-fitted vectors)

Rows: 51 clean golden + 15 dev synonym rows (no held-out rows). Default config (embedding off) plus the backoff.

Backoff off: accuracy 0.924 (wrong: g02-synonym:ANSWER->REFUSE_NO_EVIDENCE, g24-synonym:ANSWER->REFUSE_UNGROUNDED, g35-synonym:REFUSE_CANARY->REFUSE_UNGROUNDED, g39-synonym:ANSWER->REFUSE_UNGROUNDED, g48-synonym:REFUSE_PII->REFUSE_UNGROUNDED).

Chosen: threshold **0.88**, max_neighbours **1**, scope **unknown + known words** (calibration accuracy 0.939; optimal run 0.79-0.97). Default on: **True**.

| scope | max_neighbours | threshold | accuracy | clean | fail-open | spurious write | wrong |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| unknown | 1 | 0.50 | 0.864 | 0.922 | 0 | 0 | clean-g14:REFUSE_NO_EVIDENCE->REFUSE_UNGROUNDED, clean-g15:REFUSE_NO_EVIDENCE->REFUSE_UNGROUNDED, clean-g16:REFUSE_NO_EVIDENCE->REFUSE_UNGROUNDED, clean-g21:REFUSE_NO_EVIDENCE->REFUSE_UNGROUNDED, g02-synonym:ANSWER->REFUSE_UNGROUNDED, g24-synonym:ANSWER->REFUSE_UNGROUNDED, g35-synonym:REFUSE_CANARY->REFUSE_UNGROUNDED, g39-synonym:ANSWER->REFUSE_UNGROUNDED, g48-synonym:REFUSE_PII->REFUSE_UNGROUNDED |
| unknown | 1 | 0.55 | 0.879 | 0.941 | 0 | 0 | clean-g15:REFUSE_NO_EVIDENCE->REFUSE_UNGROUNDED, clean-g16:REFUSE_NO_EVIDENCE->REFUSE_UNGROUNDED, clean-g21:REFUSE_NO_EVIDENCE->REFUSE_UNGROUNDED, g02-synonym:ANSWER->REFUSE_UNGROUNDED, g24-synonym:ANSWER->REFUSE_UNGROUNDED, g35-synonym:REFUSE_CANARY->REFUSE_UNGROUNDED, g39-synonym:ANSWER->REFUSE_UNGROUNDED, g48-synonym:REFUSE_PII->REFUSE_UNGROUNDED |
| unknown | 1 | 0.62 | 0.894 | 0.961 | 0 | 0 | clean-g15:REFUSE_NO_EVIDENCE->REFUSE_UNGROUNDED, clean-g16:REFUSE_NO_EVIDENCE->REFUSE_UNGROUNDED, g02-synonym:ANSWER->REFUSE_UNGROUNDED, g24-synonym:ANSWER->REFUSE_UNGROUNDED, g35-synonym:REFUSE_CANARY->REFUSE_UNGROUNDED, g39-synonym:ANSWER->REFUSE_UNGROUNDED, g48-synonym:REFUSE_PII->REFUSE_UNGROUNDED |
| unknown | 1 | 0.65 | 0.894 | 0.961 | 0 | 0 | clean-g15:REFUSE_NO_EVIDENCE->REFUSE_UNGROUNDED, clean-g16:REFUSE_NO_EVIDENCE->REFUSE_UNGROUNDED, g02-synonym:ANSWER->REFUSE_NO_EVIDENCE, g24-synonym:ANSWER->REFUSE_UNGROUNDED, g35-synonym:REFUSE_CANARY->REFUSE_UNGROUNDED, g39-synonym:ANSWER->REFUSE_UNGROUNDED, g48-synonym:REFUSE_PII->REFUSE_UNGROUNDED |
| unknown | 1 | 0.73 | 0.909 | 0.980 | 0 | 0 | clean-g15:REFUSE_NO_EVIDENCE->REFUSE_UNGROUNDED, g02-synonym:ANSWER->REFUSE_NO_EVIDENCE, g24-synonym:ANSWER->REFUSE_UNGROUNDED, g35-synonym:REFUSE_CANARY->REFUSE_UNGROUNDED, g39-synonym:ANSWER->REFUSE_UNGROUNDED, g48-synonym:REFUSE_PII->REFUSE_UNGROUNDED |
| unknown | 1 | 0.79 | 0.924 | 1.000 | 0 | 0 | g02-synonym:ANSWER->REFUSE_NO_EVIDENCE, g24-synonym:ANSWER->REFUSE_UNGROUNDED, g35-synonym:REFUSE_CANARY->REFUSE_UNGROUNDED, g39-synonym:ANSWER->REFUSE_UNGROUNDED, g48-synonym:REFUSE_PII->REFUSE_UNGROUNDED |
| unknown | 3 | 0.50 | 0.864 | 0.922 | 0 | 0 | clean-g14:REFUSE_NO_EVIDENCE->REFUSE_UNGROUNDED, clean-g15:REFUSE_NO_EVIDENCE->REFUSE_UNGROUNDED, clean-g16:REFUSE_NO_EVIDENCE->REFUSE_UNGROUNDED, clean-g21:REFUSE_NO_EVIDENCE->REFUSE_UNGROUNDED, g02-synonym:ANSWER->REFUSE_UNGROUNDED, g24-synonym:ANSWER->REFUSE_UNGROUNDED, g35-synonym:REFUSE_CANARY->REFUSE_UNGROUNDED, g39-synonym:ANSWER->REFUSE_UNGROUNDED, g48-synonym:REFUSE_PII->REFUSE_UNGROUNDED |
| unknown | 3 | 0.55 | 0.879 | 0.941 | 0 | 0 | clean-g15:REFUSE_NO_EVIDENCE->REFUSE_UNGROUNDED, clean-g16:REFUSE_NO_EVIDENCE->REFUSE_UNGROUNDED, clean-g21:REFUSE_NO_EVIDENCE->REFUSE_UNGROUNDED, g02-synonym:ANSWER->REFUSE_UNGROUNDED, g24-synonym:ANSWER->REFUSE_UNGROUNDED, g35-synonym:REFUSE_CANARY->REFUSE_UNGROUNDED, g39-synonym:ANSWER->REFUSE_UNGROUNDED, g48-synonym:REFUSE_PII->REFUSE_UNGROUNDED |
| unknown | 3 | 0.62 | 0.894 | 0.961 | 0 | 0 | clean-g15:REFUSE_NO_EVIDENCE->REFUSE_UNGROUNDED, clean-g16:REFUSE_NO_EVIDENCE->REFUSE_UNGROUNDED, g02-synonym:ANSWER->REFUSE_UNGROUNDED, g24-synonym:ANSWER->REFUSE_UNGROUNDED, g35-synonym:REFUSE_CANARY->REFUSE_UNGROUNDED, g39-synonym:ANSWER->REFUSE_UNGROUNDED, g48-synonym:REFUSE_PII->REFUSE_UNGROUNDED |
| unknown | 3 | 0.65 | 0.894 | 0.961 | 0 | 0 | clean-g15:REFUSE_NO_EVIDENCE->REFUSE_UNGROUNDED, clean-g16:REFUSE_NO_EVIDENCE->REFUSE_UNGROUNDED, g02-synonym:ANSWER->REFUSE_NO_EVIDENCE, g24-synonym:ANSWER->REFUSE_UNGROUNDED, g35-synonym:REFUSE_CANARY->REFUSE_UNGROUNDED, g39-synonym:ANSWER->REFUSE_UNGROUNDED, g48-synonym:REFUSE_PII->REFUSE_UNGROUNDED |
| unknown | 3 | 0.73 | 0.909 | 0.980 | 0 | 0 | clean-g15:REFUSE_NO_EVIDENCE->REFUSE_UNGROUNDED, g02-synonym:ANSWER->REFUSE_NO_EVIDENCE, g24-synonym:ANSWER->REFUSE_UNGROUNDED, g35-synonym:REFUSE_CANARY->REFUSE_UNGROUNDED, g39-synonym:ANSWER->REFUSE_UNGROUNDED, g48-synonym:REFUSE_PII->REFUSE_UNGROUNDED |
| unknown | 3 | 0.79 | 0.924 | 1.000 | 0 | 0 | g02-synonym:ANSWER->REFUSE_NO_EVIDENCE, g24-synonym:ANSWER->REFUSE_UNGROUNDED, g35-synonym:REFUSE_CANARY->REFUSE_UNGROUNDED, g39-synonym:ANSWER->REFUSE_UNGROUNDED, g48-synonym:REFUSE_PII->REFUSE_UNGROUNDED |
| unknown+known | 1 | 0.50 | 0.879 | 0.922 | 0 | 0 | clean-g14:REFUSE_NO_EVIDENCE->REFUSE_UNGROUNDED, clean-g15:REFUSE_NO_EVIDENCE->REFUSE_UNGROUNDED, clean-g16:REFUSE_NO_EVIDENCE->REFUSE_UNGROUNDED, clean-g21:REFUSE_NO_EVIDENCE->REFUSE_UNGROUNDED, g02-synonym:ANSWER->REFUSE_UNGROUNDED, g24-synonym:ANSWER->REFUSE_UNGROUNDED, g35-synonym:REFUSE_CANARY->REFUSE_UNGROUNDED, g48-synonym:REFUSE_PII->REFUSE_UNGROUNDED |
| unknown+known | 1 | 0.55 | 0.894 | 0.941 | 0 | 0 | clean-g15:REFUSE_NO_EVIDENCE->REFUSE_UNGROUNDED, clean-g16:REFUSE_NO_EVIDENCE->REFUSE_UNGROUNDED, clean-g21:REFUSE_NO_EVIDENCE->REFUSE_UNGROUNDED, g02-synonym:ANSWER->REFUSE_UNGROUNDED, g24-synonym:ANSWER->REFUSE_UNGROUNDED, g35-synonym:REFUSE_CANARY->REFUSE_UNGROUNDED, g48-synonym:REFUSE_PII->REFUSE_UNGROUNDED |
| unknown+known | 1 | 0.62 | 0.909 | 0.961 | 0 | 0 | clean-g15:REFUSE_NO_EVIDENCE->REFUSE_UNGROUNDED, clean-g16:REFUSE_NO_EVIDENCE->REFUSE_UNGROUNDED, g02-synonym:ANSWER->REFUSE_UNGROUNDED, g24-synonym:ANSWER->REFUSE_UNGROUNDED, g35-synonym:REFUSE_CANARY->REFUSE_UNGROUNDED, g48-synonym:REFUSE_PII->REFUSE_UNGROUNDED |
| unknown+known | 1 | 0.65 | 0.909 | 0.961 | 0 | 0 | clean-g15:REFUSE_NO_EVIDENCE->REFUSE_UNGROUNDED, clean-g16:REFUSE_NO_EVIDENCE->REFUSE_UNGROUNDED, g02-synonym:ANSWER->REFUSE_NO_EVIDENCE, g24-synonym:ANSWER->REFUSE_UNGROUNDED, g35-synonym:REFUSE_CANARY->REFUSE_UNGROUNDED, g48-synonym:REFUSE_PII->REFUSE_UNGROUNDED |
| unknown+known | 1 | 0.73 | 0.924 | 0.980 | 0 | 0 | clean-g15:REFUSE_NO_EVIDENCE->REFUSE_UNGROUNDED, g02-synonym:ANSWER->REFUSE_NO_EVIDENCE, g24-synonym:ANSWER->REFUSE_UNGROUNDED, g35-synonym:REFUSE_CANARY->REFUSE_UNGROUNDED, g48-synonym:REFUSE_PII->REFUSE_UNGROUNDED |
| unknown+known | 1 | 0.79 | 0.939 | 1.000 | 0 | 0 | g02-synonym:ANSWER->REFUSE_NO_EVIDENCE, g24-synonym:ANSWER->REFUSE_UNGROUNDED, g35-synonym:REFUSE_CANARY->REFUSE_UNGROUNDED, g48-synonym:REFUSE_PII->REFUSE_UNGROUNDED |
| unknown+known | 1 | 0.98 | 0.924 | 1.000 | 0 | 0 | g02-synonym:ANSWER->REFUSE_NO_EVIDENCE, g24-synonym:ANSWER->REFUSE_UNGROUNDED, g35-synonym:REFUSE_CANARY->REFUSE_UNGROUNDED, g39-synonym:ANSWER->REFUSE_UNGROUNDED, g48-synonym:REFUSE_PII->REFUSE_UNGROUNDED |
| unknown+known | 3 | 0.50 | 0.879 | 0.922 | 0 | 0 | clean-g14:REFUSE_NO_EVIDENCE->REFUSE_UNGROUNDED, clean-g15:REFUSE_NO_EVIDENCE->REFUSE_UNGROUNDED, clean-g16:REFUSE_NO_EVIDENCE->REFUSE_UNGROUNDED, clean-g21:REFUSE_NO_EVIDENCE->REFUSE_UNGROUNDED, g02-synonym:ANSWER->REFUSE_UNGROUNDED, g24-synonym:ANSWER->REFUSE_UNGROUNDED, g35-synonym:REFUSE_CANARY->REFUSE_UNGROUNDED, g48-synonym:REFUSE_PII->REFUSE_UNGROUNDED |
| unknown+known | 3 | 0.55 | 0.894 | 0.941 | 0 | 0 | clean-g15:REFUSE_NO_EVIDENCE->REFUSE_UNGROUNDED, clean-g16:REFUSE_NO_EVIDENCE->REFUSE_UNGROUNDED, clean-g21:REFUSE_NO_EVIDENCE->REFUSE_UNGROUNDED, g02-synonym:ANSWER->REFUSE_UNGROUNDED, g24-synonym:ANSWER->REFUSE_UNGROUNDED, g35-synonym:REFUSE_CANARY->REFUSE_UNGROUNDED, g48-synonym:REFUSE_PII->REFUSE_UNGROUNDED |
| unknown+known | 3 | 0.62 | 0.909 | 0.961 | 0 | 0 | clean-g15:REFUSE_NO_EVIDENCE->REFUSE_UNGROUNDED, clean-g16:REFUSE_NO_EVIDENCE->REFUSE_UNGROUNDED, g02-synonym:ANSWER->REFUSE_UNGROUNDED, g24-synonym:ANSWER->REFUSE_UNGROUNDED, g35-synonym:REFUSE_CANARY->REFUSE_UNGROUNDED, g48-synonym:REFUSE_PII->REFUSE_UNGROUNDED |
| unknown+known | 3 | 0.65 | 0.909 | 0.961 | 0 | 0 | clean-g15:REFUSE_NO_EVIDENCE->REFUSE_UNGROUNDED, clean-g16:REFUSE_NO_EVIDENCE->REFUSE_UNGROUNDED, g02-synonym:ANSWER->REFUSE_NO_EVIDENCE, g24-synonym:ANSWER->REFUSE_UNGROUNDED, g35-synonym:REFUSE_CANARY->REFUSE_UNGROUNDED, g48-synonym:REFUSE_PII->REFUSE_UNGROUNDED |
| unknown+known | 3 | 0.73 | 0.924 | 0.980 | 0 | 0 | clean-g15:REFUSE_NO_EVIDENCE->REFUSE_UNGROUNDED, g02-synonym:ANSWER->REFUSE_NO_EVIDENCE, g24-synonym:ANSWER->REFUSE_UNGROUNDED, g35-synonym:REFUSE_CANARY->REFUSE_UNGROUNDED, g48-synonym:REFUSE_PII->REFUSE_UNGROUNDED |
| unknown+known | 3 | 0.79 | 0.939 | 1.000 | 0 | 0 | g02-synonym:ANSWER->REFUSE_NO_EVIDENCE, g24-synonym:ANSWER->REFUSE_UNGROUNDED, g35-synonym:REFUSE_CANARY->REFUSE_UNGROUNDED, g48-synonym:REFUSE_PII->REFUSE_UNGROUNDED |
| unknown+known | 3 | 0.98 | 0.924 | 1.000 | 0 | 0 | g02-synonym:ANSWER->REFUSE_NO_EVIDENCE, g24-synonym:ANSWER->REFUSE_UNGROUNDED, g35-synonym:REFUSE_CANARY->REFUSE_UNGROUNDED, g39-synonym:ANSWER->REFUSE_UNGROUNDED, g48-synonym:REFUSE_PII->REFUSE_UNGROUNDED |

## Dev pairs, word level (63 dev replacement words)

Top table substitute is a content word of the replaced key: **5/63**; an inflection of the word itself: 11; another word: 19 (of which >= the chosen threshold: 4); nothing >= the 0.50 floor: 28. 'Another word' is not always wrong (calendar -> timeline), but several are wrong-sense substitutes (instances -> example, servicing -> service).

| pair | word | top substitute | cosine | kind |
| --- | --- | --- | ---: | --- |
| `page->alert` | alert | reminder | 0.545 | other |
| `patch->update` | update | updates | 0.993 | inflection |
| `replicas->pods` | pods | - | - | none |
| `replicas->instances` | instances | example | 0.965 | other |
| `enabled->switched on` | switched | switch | 0.935 | inflection |
| `utilization->usage` | usage | use | 0.977 | inflection |
| `utilization->saturation` | saturation | - | - | none |
| `mitigation->remediation` | remediation | - | - | none |
| `recommend->suggest` | suggest | proposal | 0.619 | other |
| `runbook->playbook` | playbook | - | - | none |
| `procedure->process` | process | treat | 0.773 | other |
| `email->e-mail` | e-mail | - | - | none |
| `token->secret` | secret | secrets | 0.964 | inflection |
| `schedule->calendar` | calendar | timeline | 0.923 | other |
| `window->timeframe` | timeframe | timeline | 0.990 | other |
| `on-call->on-duty` | on-duty | - | - | none |
| `on-call->pager` | pager | - | - | none |
| `primary->lead` | lead | leading | 0.646 | inflection |
| `outage->incident` | incident | event | 0.824 | other |
| `deploy->release` | release | - | - | none |
| `remaining->leftover` | leftover | remaining | 0.540 | key |
| `current->present` | present | - | - | none |
| `current->latest` | latest | last | 0.783 | other |
| `freeze->lockdown` | lockdown | - | - | none |
| `freeze->moratorium` | moratorium | - | - | none |
| `production->prod` | prod | - | - | none |
| `maintenance->upkeep` | upkeep | maintenance | 0.952 | key |
| `maintenance->servicing` | servicing | service | 0.999 | inflection |
| `database->datastore` | datastore | - | - | none |
| `feature flag->feature toggle` | toggle | switch | 0.641 | other |
| `feature flag->feature switch` | switch | change | 0.520 | other |
| `flag->toggle` | toggle | switch | 0.641 | other |
| `flag->switch` | switch | change | 0.520 | other |
| `rollback->revert` | revert | returning | 0.957 | other |
| `rollback->undo` | undo | - | - | none |
| `owns->maintains` | maintains | retained | 0.621 | other |
| `directory->listing` | listing | lists | 0.952 | inflection |
| `reset->clear` | clear | manifest | 0.654 | other |
| `drain->clear` | clear | manifest | 0.654 | other |
| `target->goal` | goal | target | 0.949 | key |
| `request rate->throughput` | throughput | - | - | none |
| `endpoint->URL` | url | - | - | none |
| `key->secret` | secret | secrets | 0.964 | inflection |
| `path->route` | route | path | 0.972 | key |
| `path->location` | location | - | - | none |
| `route->URL` | url | - | - | none |
| `gateway->proxy` | proxy | replacement | 0.718 | other |
| `gateway->edge` | edge | - | - | none |
| `start->begin` | begin | start | 0.941 | key |
| `error budget->SLO headroom` | slo | - | - | none |
| `error budget->SLO headroom` | headroom | - | - | none |
| `error budget->error allowance` | allowance | - | - | none |
| `service->app` | app | - | - | none |
| `flush->clear` | clear | manifest | 0.654 | other |
| `webhook->hook` | hook | hooks | 0.914 | inflection |
| `chargeback->dispute` | dispute | - | - | none |
| `chargeback->refund` | refund | refunds | 0.980 | inflection |
| `playbook->runbook` | runbook | - | - | none |
| `checkpoint->snapshot` | snapshot | freeze | 0.660 | other |
| `handshake->setup` | setup | set | 0.615 | inflection |
| `setting->parameter` | parameter | - | - | none |
| `qps->throughput` | throughput | - | - | none |
| `stickiness->pinning` | pinning | - | - | none |
